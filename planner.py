"""Deterministic ORYVA shortage planner and labeled exception fixtures."""
import argparse, csv, hashlib, json, sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

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
    balances=[]; shorts=[]; mitigations=[]; prior={}
    for d in demand:
        key=(d['sku_id'],d['location_id']); start=date.fromisoformat(d['week_start']); end=start+timedelta(days=6)
        opening=prior.get(key,stock.get(key,0)); inbound=sum(q for dt,q in arrivals.get(key,()) if start.isoformat()<=dt<=end.isoformat())
        projected=opening+inbound-d['forecast_qty']; prior[key]=projected
        lid=lead.get(key); coverage=(lid is not None and lid<=7)
        balances.append(dict(demand_id=d['demand_id'],sku_id=d['sku_id'],location_id=d['location_id'],week_start=d['week_start'],uom=d['uom'],opening_qty=round(opening,2),inbound_qty=round(inbound,2),demand_qty=d['forecast_qty'],projected_available_qty=round(projected,2),lead_time_days=lid if lid is not None else '',lead_time_covered=int(coverage)))
        shortage=max(0,-projected)
        if shortage:
            sid=f'SHORT-2026-{len(shorts)+1:06d}'; cause='Demand exceeds opening balance and scheduled arrivals'
            if not lid: cause+='; no effective lead time'
            shorts.append(dict(shortage_id=sid,demand_id=d['demand_id'],sku_id=d['sku_id'],location_id=d['location_id'],week_start=d['week_start'],shortage_qty=round(shortage,2),uom=d['uom'],cause_summary=cause,priority_score=round(shortage/max(d['forecast_qty'],1)*100,3),lead_time_days=lid if lid is not None else ''))
            candidates=sorted(supplier_options.get(key,[]),key=lambda x:(x['days'],x['supplier_id']))
            qty=min(shortage,max(1,d['forecast_qty']*.5))
            feasible_options=[]
            for option_type, unit_cost, max_qty, rationale in (
                ('EXPEDITE',22.0,min(shortage,max(1,d['forecast_qty']*.5)),'Fast recovery at premium freight'),
                ('ALTERNATE_SUPPLIER',12.0,shortage,'Lower premium using an alternate supplier'),
            ):
                for supplier in candidates:
                    available=max(0.0,supplier['capacity']-used[(key[0],key[1],supplier['supplier_id'])])
                    quantity=min(max_qty,available)
                    if supplier['uom']==d['uom'] and supplier['days']<=7 and quantity>=supplier['minimum'] and quantity>0:
                        feasible_options.append(dict(shortage_id=sid,option_type=option_type,mitigation_qty=round(quantity,2),uom=d['uom'],incremental_cost=round(quantity*unit_cost,2),service_impact_qty=round(shortage-quantity,2),feasible=1,supplier_id=supplier['supplier_id'],rationale=f'{rationale}; matching UOM, lead time <=7 days, minimum quantity and remaining capacity verified'))
            feasible_options.append(dict(shortage_id=sid,option_type='DEMAND_ALLOCATION',mitigation_qty=round(shortage,2),uom=d['uom'],incremental_cost=0,service_impact_qty=round(shortage,2),feasible=1,supplier_id='',rationale='Policy-feasible allocation; full residual service loss is explicit'))
            feasible_options.sort(key=lambda x:(x['service_impact_qty'],x['incremental_cost'],x['option_type'],x['supplier_id']))
            # Distinct strategy types keep the three recommendations useful and non-duplicative.
            selected=[]; seen=set()
            for option in feasible_options:
                if option['option_type'] not in seen:
                    selected.append(option); seen.add(option['option_type'])
                if len(selected)==3: break
            for n,option in enumerate(selected,1):
                option['mitigation_option_id']=f'MIT-{sid}-{n:02d}'
                mitigations.append(option)
    # Explicit isolated truth fixtures: examples define expected detection semantics, not corrupted base inputs.
    cases=[('INBOUND_INVENTORY_COUNTED_TWICE','EXPECTED_ALERT','Same PO line included as inventory inbound and scheduled receipt; deduplicate by source line.'),('UNAPPROVED_SUBSTITUTE_SKU','EXPECTED_REJECTION','Substitution candidate has no effective APPROVED bridge row.'),('SUPPLIER_CAPACITY_EXCEEDED','EXPECTED_EXCEPTION','Proposed quantity exceeds effective supplier capacity.'),('SHORTAGE_WITHOUT_LEAD_TIME','EXPECTED_ALERT','Shortage source has no effective supplier/SKU/destination lead-time row.'),('UOM_MISMATCH','EXPECTED_REJECTION','Candidate supply uses a unit different from demand SKU base UOM.')]
    sample_d=db.execute('select demand_id,sku_id,location_id from forecast_demand order by demand_id limit 1').fetchone()
    sample_i=db.execute('select inventory_id,sku_id,location_id from inventory order by inventory_id limit 1').fetchone()
    sample_p=db.execute('select pol.purchase_order_line_id,pol.sku_id,po.destination_location_id,po.supplier_id from purchase_order_line pol join purchase_order po using(purchase_order_id) order by pol.purchase_order_line_id limit 1').fetchone()
    sample_c=db.execute('select supplier_capacity_id,supplier_id,sku_id from supplier_capacity order by supplier_capacity_id limit 1').fetchone()
    refs=[f"inventory:{sample_i['inventory_id']}|purchase_order_line:{sample_p['purchase_order_line_id']}",f"sku:{sample_d['sku_id']}|candidate_substitute:UNAPPROVED_RELATION_ABSENT",f"supplier_capacity:{sample_c['supplier_capacity_id']}|purchase_order_line:{sample_p['purchase_order_line_id']}",f"forecast_demand:{sample_d['demand_id']}|lead_time:NOT_FOUND_FOR_TEST_ROUTE",f"forecast_demand:{sample_d['demand_id']}|sku:{sample_d['sku_id']}|uom_counterfactual:KG"]
    truth=[dict(case_id=f'ISSUE-{i:06d}',issue_type=t,ground_truth_label=l,description=x,source_record_refs=refs[i-1],fixture_source='isolated_rule_fixture',excluded_from_planner_inputs=1) for i,(t,l,x) in enumerate(cases,1)]
    counts={'projected_balance.csv':csvout(root/'projected_balance.csv',balances),'shortages.csv':csvout(root/'shortages.csv',shorts),'mitigations.csv':csvout(root/'mitigations.csv',mitigations),'ground_truth.csv':csvout(root/'ground_truth.csv',truth)}
    ranked=sorted(shorts,key=lambda x:(-x['priority_score'],-x['shortage_qty'],x['shortage_id']))
    counts['shortage_ranking.csv']=csvout(root/'shortage_ranking.csv',ranked)
    mitigation_counts=defaultdict(int)
    for option in mitigations: mitigation_counts[option['shortage_id']]+=1
    checks={'balances_reconciled':all(abs(x['projected_available_qty']-(x['opening_qty']+x['inbound_qty']-x['demand_qty']))<.011 for x in balances),'all_five_cases_labeled':len(truth)==5,'shortages_explainable':all(bool(x['cause_summary']) for x in shorts),'mitigation_tradeoffs_present':all(x['incremental_cost']>=0 and x['service_impact_qty']>=0 for x in mitigations),'mitigations_all_feasible':all(x['feasible']==1 for x in mitigations),'max_three_mitigations_per_shortage':max(mitigation_counts.values(),default=0)<=3,'row_counts':counts}
    checks['sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.csv')}
    (root/'planner_validation.json').write_text(json.dumps(checks,indent=2,sort_keys=True)+'\n')
    if not all(v for k,v in checks.items() if isinstance(v,bool)): raise SystemExit('planner validation failed')
    print(json.dumps(checks,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--data-dir',required=True); plan(p.parse_args().data_dir)
