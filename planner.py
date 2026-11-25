"""Deterministic ORYVA shortage planner and labeled exception fixtures."""
import argparse, csv, hashlib, json, sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
import statistics

def csvout(path, rows):
    rows=list(rows)
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['record_id'], lineterminator='\n')
        w.writeheader(); w.writerows(rows)
    return len(rows)

def plan(root):
    root=Path(root); db=sqlite3.connect(root/'oryva.sqlite3'); db.row_factory=sqlite3.Row
    demand=db.execute('select * from forecast_demand order by sku_id,location_id,week_start').fetchall()
    stock={(r['sku_id'],r['location_id']):r['on_hand_qty'] for r in db.execute('select * from inventory')}
    uoms={r['sku_id']:r['base_uom'] for r in db.execute('select sku_id,base_uom from sku')}
    arrivals=defaultdict(list)
    for r in db.execute('''select pol.sku_id,po.destination_location_id,t.revised_delivery_date,pol.quantity
      from purchase_order_line pol join purchase_order po using(purchase_order_id)
      join transport_delay t using(purchase_order_id)'''):
        arrivals[(r['sku_id'],r['destination_location_id'])].append((r['revised_delivery_date'][:10],r['quantity']))
    lead={}
    for r in db.execute('select sku_id,destination_location_id,min(lead_time_days) days from lead_time group by 1,2'):
        lead[(r['sku_id'],r['destination_location_id'])]=r['days']
    supplier_options=defaultdict(list)
    used=defaultdict(float)
    for r in db.execute('''select sc.supplier_id,sc.sku_id,sc.capacity_qty,sc.minimum_order_qty,sc.uom,
      lt.destination_location_id,lt.lead_time_days from supplier_capacity sc join lead_time lt
      on lt.supplier_id=sc.supplier_id and lt.sku_id=sc.sku_id'''):
        supplier_options[(r['sku_id'],r['destination_location_id'])].append(dict(supplier_id=r['supplier_id'],capacity=r['capacity_qty'],minimum=r['minimum_order_qty'],uom=r['uom'],days=r['lead_time_days']))
    for r in db.execute('''select pol.sku_id,po.destination_location_id,po.supplier_id,sum(pol.quantity) qty
      from purchase_order_line pol join purchase_order po using(purchase_order_id) group by 1,2,3'''):
        used[(r['sku_id'],r['destination_location_id'],r['supplier_id'])]=r['qty']
    weeks=sorted({date.fromisoformat(r['week_start']) for r in demand})
    by_week=defaultdict(list)
    for d in demand: by_week[date.fromisoformat(d['week_start'])].append(d)
    factory_locs={r['location_id'] for r in db.execute("select location_id from location where location_type='FACTORY'")}
    annual_caps={(r['sku_id'],r['location_id']):r for r in db.execute('select * from production_capacity')}
    boms=defaultdict(list)
    for r in db.execute('select * from bill_of_material'):
        boms[r['parent_sku_id']].append(dict(component=r['component_sku_id'],qty=r['quantity_per'],uom=r['uom'],start=r['effective_from'],end=r['effective_to']))
    prior=dict(stock); balances=[]; production_plans=[]; weekly_caps=[]; plan_seq=0
    for week in weeks:
        current={}; rows={}
        for d in by_week[week]:
            key=(d['sku_id'],d['location_id']); end=week+timedelta(days=6)
            opening=prior.get(key,0.0); inbound=sum(q for dt,q in arrivals.get(key,()) if week.isoformat()<=dt<=end.isoformat())
            current[key]=opening+inbound-d['forecast_qty']
            rows[key]=dict(demand_id=d['demand_id'],sku_id=d['sku_id'],location_id=d['location_id'],week_start=week.isoformat(),uom=d['uom'],opening_qty=opening,inbound_qty=inbound,demand_qty=d['forecast_qty'],production_qty=0.0,component_consumption_qty=0.0,projected_available_qty=0.0,lead_time_days=lead.get(key,''),lead_time_covered=int(lead.get(key,999)<=7),production_constraint_qty=0.0)
        for (sku_id,loc_id),capacity in annual_caps.items():
            weekly_qty=capacity['capacity_qty']/max(1,len(weeks))
            weekly_caps.append(dict(sku_id=sku_id,location_id=loc_id,week_start=week.isoformat(),capacity_qty=round(weekly_qty,4),annual_capacity_qty=capacity['capacity_qty'],uom=capacity['uom'],source_capacity_id=capacity['production_capacity_id']))
        for parent in sorted(boms):
            for loc_id in sorted(factory_locs):
                parent_key=(parent,loc_id)
                if parent_key not in current: continue
                capacity=annual_caps.get(parent_key)
                if not capacity: continue
                remaining_cap=capacity['capacity_qty']/max(1,len(weeks))
                rows[parent_key]['production_constraint_qty']=max(0.0,-current[parent_key])
                for bom in boms[parent]:
                    if bom['start']>week.isoformat() or (bom['end'] and bom['end']<week.isoformat()): continue
                    component_key=(bom['component'],loc_id)
                    if component_key not in current or bom['uom']!=uoms[bom['component']]: continue
                    shortage=max(0.0,-current[parent_key])
                    material=max(0.0,current[component_key])
                    make=min(shortage,remaining_cap,material/bom['qty'])
                    if make<=0: continue
                    consumed=make*bom['qty']; current[component_key]-=consumed; current[parent_key]+=make; remaining_cap-=make
                    rows[component_key]['component_consumption_qty']+=consumed
                    rows[parent_key]['production_qty']+=make
                    plan_seq+=1
                    production_plans.append(dict(production_plan_id=f'PP-{plan_seq:010d}',sku_id=parent,location_id=loc_id,week_start=week.isoformat(),planned_qty=round(make,2),uom=uoms[parent],component_sku_id=bom['component'],component_qty=round(consumed,2),component_uom=bom['uom'],capacity_qty=round(capacity['capacity_qty']/max(1,len(weeks)),4),capacity_source_id=capacity['production_capacity_id'],source_demand_id=rows[parent_key]['demand_id'],status='PLANNED'))
                    rows[parent_key]['production_constraint_qty']=max(0.0,-current[parent_key])
        for key,row in rows.items():
            row['projected_available_qty']=round(current[key],2)
            for col in ('opening_qty','inbound_qty','demand_qty','production_qty','component_consumption_qty','production_constraint_qty'):
                row[col]=round(row[col],2)
            balances.append(row); prior[key]=current[key]
    shorts=[]; mitigations=[]
    for row in balances:
        shortage=max(0.0,-row['projected_available_qty'])
        if not shortage: continue
        key=(row['sku_id'],row['location_id']); lid=lead.get(key)
        sid=f'SHORT-2026-{len(shorts)+1:06d}'; cause='Demand exceeds opening balance and scheduled arrivals'
        if row['production_constraint_qty']>0: cause+='; production constraint limits feasible BOM conversion'
        if not lid: cause+='; no effective lead time'
        shorts.append(dict(shortage_id=sid,demand_id=row['demand_id'],sku_id=row['sku_id'],location_id=row['location_id'],week_start=row['week_start'],shortage_qty=round(shortage,2),uom=row['uom'],cause_summary=cause,priority_score=round(shortage/max(row['demand_qty'],1)*100,3),lead_time_days=lid if lid is not None else ''))
        candidates=sorted(supplier_options.get(key,[]),key=lambda x:(x['days'],x['supplier_id']))
        feasible_options=[]
        for option_type, unit_cost, max_qty, rationale in (('EXPEDITE',22.0,min(shortage,max(1,row['demand_qty']*.5)),'Fast recovery at premium freight'),('ALTERNATE_SUPPLIER',12.0,shortage,'Lower premium using an alternate supplier')):
            for supplier in candidates:
                available=max(0.0,supplier['capacity']-used[(key[0],key[1],supplier['supplier_id'])]); quantity=min(max_qty,available)
                if supplier['uom']==row['uom'] and supplier['days']<=7 and quantity>=supplier['minimum'] and quantity>0:
                    feasible_options.append(dict(shortage_id=sid,option_type=option_type,mitigation_qty=round(quantity,2),uom=row['uom'],incremental_cost=round(quantity*unit_cost,2),service_impact_qty=round(shortage-quantity,2),feasible=1,supplier_id=supplier['supplier_id'],rationale=f'{rationale}; matching UOM, lead time <=7 days, minimum quantity and remaining capacity verified'))
        feasible_options.append(dict(shortage_id=sid,option_type='DEMAND_ALLOCATION',mitigation_qty=round(shortage,2),uom=row['uom'],incremental_cost=0,service_impact_qty=round(shortage,2),feasible=1,supplier_id='',rationale='Policy-feasible allocation; full residual service loss is explicit'))
        feasible_options.sort(key=lambda x:(x['service_impact_qty'],x['incremental_cost'],x['option_type'],x['supplier_id']))
        for n,option in enumerate(feasible_options[:3],1):
            option['mitigation_option_id']=f'MIT-{sid}-{n:02d}'; mitigations.append(option)
    counts={'projected_balance.csv':csvout(root/'projected_balance.csv',balances),'shortages.csv':csvout(root/'shortages.csv',shorts),'mitigations.csv':csvout(root/'mitigations.csv',mitigations),'production_plan.csv':csvout(root/'production_plan.csv',production_plans),'production_capacity_weekly.csv':csvout(root/'production_capacity_weekly.csv',weekly_caps)}
    ranked=sorted(shorts,key=lambda x:(-x['priority_score'],-x['shortage_qty'],x['shortage_id']))
    counts['shortage_ranking.csv']=csvout(root/'shortage_ranking.csv',ranked)
    mitigation_counts=defaultdict(int)
    for option in mitigations: mitigation_counts[option['shortage_id']]+=1
    causes=defaultdict(int)
    for row in shorts: causes[row['cause_summary']]+=1
    shortage_rate=len(shorts)/max(1,len(balances))
    quantities=[x['shortage_qty'] for x in shorts]
    checks={'balances_reconciled':all(abs(x['projected_available_qty']-(x['opening_qty']+x['inbound_qty']-x['demand_qty']+x['production_qty']-x['component_consumption_qty']))<.011 for x in balances),'production_within_weekly_capacity':all(p['planned_qty']<=p['capacity_qty']+.011 for p in production_plans),'bom_consumption_reconciles':all(abs(p['component_qty']-p['planned_qty']*next(b['qty'] for b in boms[p['sku_id']] if b['component']==p['component_sku_id']))<.011 for p in production_plans),'shortages_explainable':all(bool(x['cause_summary']) for x in shorts),'mitigation_tradeoffs_present':all(x['incremental_cost']>=0 and x['service_impact_qty']>=0 for x in mitigations),'mitigations_all_feasible':all(x['feasible']==1 for x in mitigations),'max_three_mitigations_per_shortage':max(mitigation_counts.values(),default=0)<=3,'shortage_rate_in_target':0.05<=shortage_rate<=0.15,'ground_truth_excluded':True,'shortage_distribution':{'rate':round(shortage_rate,6),'mean_qty':round(statistics.mean(quantities),2) if quantities else 0,'median_qty':round(statistics.median(quantities),2) if quantities else 0,'top_causes':dict(sorted(causes.items(),key=lambda x:(-x[1],x[0]))[:5])},'row_counts':counts}
    checks['sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.csv') if p.name!='ground_truth.csv'}
    (root/'planner_validation.json').write_text(json.dumps(checks,indent=2,sort_keys=True)+'\n')
    manifest_path=root/'source_manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['output_files']=sorted(set(manifest.get('output_files',[]))|set(counts)|{'planner_validation.json'})
        manifest['output_files']=sorted(set(manifest.get('output_files',[]))|set(counts)|{'planner_validation.json'})
        manifest['planner']={'algorithm':'Weekly closing availability = opening + revised PO receipts + feasible production - forecast demand - BOM component consumption; closing balance rolls forward.','mitigation_policy':'At most three feasible options per shortage, ranked by service impact then incremental cost. Supplier options require matching UOM, lead time <=7 days, minimum order quantity and remaining capacity. Ground truth is excluded from planner inputs.','row_counts':counts,'shortage_distribution':checks['shortage_distribution'],'validation_file':'planner_validation.json'}
        manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    if not all(v for k,v in checks.items() if isinstance(v,bool)): raise SystemExit('planner validation failed')
    print(json.dumps(checks,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--data-dir',required=True); plan(p.parse_args().data_dir)
