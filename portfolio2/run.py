"""Execute Portfolio 2 on disposable database copies; publish only derived results.

Python standard library only. The Portfolio 1 source database is opened read-only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import sqlite3
import statistics
import sys
from time import perf_counter_ns

PREFIX = 'Ezenduka_Chukwubuikem_301913360'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FOCUS_ITEM = 'Rice Local, short-Grained'


def sql_catalog(filename):
    text = (HERE / f'{filename.lower()}.sql').read_text(encoding='utf-8-sig')
    parts = re.split(r'^-- name: ([A-Z0-9_]+)\s*$', text, flags=re.M)
    return {parts[n]: parts[n+1].strip() for n in range(1,len(parts),2)}


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_rows(rows):
    return hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def connection(path, readonly=False):
    con = sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) if readonly else sqlite3.connect(path)
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA cache_size=-8192')
    con.execute('PRAGMA temp_store=MEMORY')
    con.execute('PRAGMA automatic_index=ON')
    return con


def result(con, sql, params):
    cursor = con.execute(sql,params)
    columns = [col[0] for col in cursor.description]
    return {'columns': columns, 'rows': [dict(zip(columns,row)) for row in cursor.fetchall()]}


def explain(con, sql, params):
    return [dict(zip(('id','parent','unused','detail'),row))
            for row in con.execute('EXPLAIN QUERY PLAN '+sql,params)]


def vm_work(con, sql, params):
    calls=0
    def tick():
        nonlocal calls
        calls += 1
        return 0
    # Prepare/warm once before the instrumented execution. Never time this callback.
    con.execute(sql,params).fetchall()
    con.set_progress_handler(tick,1)
    try:
        con.execute(sql,params).fetchall()
    finally:
        con.set_progress_handler(None,0)
    return calls


def distribution(samples):
    quartiles=statistics.quantiles(samples,n=4,method='inclusive')
    return {'median_us':statistics.median(samples), 'q1_us':quartiles[0], 'q3_us':quartiles[2],
            'min_us':min(samples),'max_us':max(samples),'round_mean_us':samples}


def benchmark(name,before,after,params,rounds,repetitions,warmups):
    con_a,sql_a=before
    con_b,sql_b=after
    a=con_a.execute(sql_a,params).fetchall()
    b=con_b.execute(sql_b,params).fetchall()
    if a!=b:
        raise AssertionError(f'{name}: before and after ordered results differ')
    plans={'before':explain(con_a,sql_a,params),'after':explain(con_b,sql_b,params)}
    for _ in range(warmups):
        con_a.execute(sql_a,params).fetchall()
        con_b.execute(sql_b,params).fetchall()
    samples={'before':[],'after':[]}
    for round_number in range(rounds):
        order=[('before',con_a,sql_a),('after',con_b,sql_b)]
        if round_number%2:
            order.reverse()
        for label,con,sql in order:
            start=perf_counter_ns()
            for _ in range(repetitions):
                con.execute(sql,params).fetchall()
            samples[label].append((perf_counter_ns()-start)/repetitions/1000)
    stats={key:distribution(values) for key,values in samples.items()}
    return {'case':name,'rows_returned':len(a),'ordered_result_sha256':digest_rows(a),
            'ordered_results_equal':True,'plans':plans, **stats,
            'before_over_after_ratio':stats['before']['median_us']/stats['after']['median_us'],
            'vm_callbacks_before':vm_work(con_a,sql_a,params),
            'vm_callbacks_after':vm_work(con_b,sql_b,params)}, a


def percentage(new,old):
    return float((Decimal(100)*(new-old)/old).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))


def independent_checks(con, outputs, params):
    """Compare all analytical queries with independently grouped Python records."""
    rows=con.execute('SELECT p.period,i.label,g.name,g.level,o.price_kobo FROM price_observation o '
                     'JOIN publication p USING(publication_id) JOIN item i USING(item_id) '
                     'JOIN geography g USING(geography_id)').fetchall()
    months=sorted({r[0] for r in rows})
    labels=sorted({r[1] for r in rows})
    expected={}
    expected['Q01_COVERAGE']=[{'period':m,'observations':sum(r[0]==m for r in rows),
       'distinct_labels':len({r[1] for r in rows if r[0]==m}),
       'national_observations':sum(r[0]==m and r[3]=='national' for r in rows),
       'zonal_observations':sum(r[0]==m and r[3]=='zone' for r in rows)} for m in months]
    expected['Q02_ITEM_AVAILABILITY']=[{'item':label,'months':len({r[0] for r in rows if r[1]==label}),
       'national_observations':sum(r[1]==label and r[3]=='national' for r in rows),
       'zonal_observations':sum(r[1]==label and r[3]=='zone' for r in rows)} for label in labels]
    series={r[0]:r[4] for r in rows if r[1]==FOCUS_ITEM and r[2]=='Nigeria'}
    changes=[]
    for month,value in sorted(series.items()):
        year,number=map(int,month.split('-'))
        previous=f'{year if number>1 else year-1:04d}-{number-1 if number>1 else 12:02d}'
        if previous in series:
            changes.append({'period':month,'preceding_month':previous,'change_percent':percentage(value,series[previous])})
    expected['Q03_MONTHLY_CHANGE']=changes
    spreads=[]
    for month in months:
        prices=[r[4] for r in rows if r[0]==month and r[1]==FOCUS_ITEM and r[3]=='zone']
        if len(prices)==6:
            spreads.append({'period':month,'zones_observed':6,'spread_percent':percentage(max(prices),min(prices))})
    expected['Q04_REGIONAL_SPREAD']=spreads
    end=params['end_period']
    zone_rows=[r for r in rows if r[0]==end and r[1]==FOCUS_ITEM and r[3]=='zone']
    ranked_values=sorted({r[4] for r in zone_rows},reverse=True)
    expected['Q05_REGIONAL_RANKING']=sorted([
       {'period':end,'zone':r[2],'price_rank':ranked_values.index(r[4])+1,
        'premium_to_national_percent':percentage(r[4],series[end])} for r in zone_rows],
       key=lambda x:(x['price_rank'],x['zone']))
    national={(r[0],r[1]):r[4] for r in rows if r[3]=='national'}
    end_changes=[]
    for label in labels:
        start_key=(params['start_period'],label)
        end_key=(end,label)
        if start_key in national and end_key in national:
            end_changes.append({'item':label,'start_period':params['start_period'],'end_period':end,
                                'change_percent':percentage(national[end_key],national[start_key])})
    expected['Q06_PERIOD_CHANGE_RANKING']=sorted(end_changes,key=lambda x:(-x['change_percent'],x['item']))[:params['top_n']]
    levels=defaultdict(set)
    for r in rows: levels[(r[0],r[1])].add(r[3])
    unmatched=Counter((r[1],r[3]) for r in rows if len(levels[(r[0],r[1])])==1)
    expected['Q07_UNMATCHED_LABELS']=[{'item':i,'level':level,'observations_without_other_level':count}
                                    for (i,level),count in sorted(unmatched.items())]
    item_spreads=[]
    for label in labels:
        prices=[r[4] for r in rows if r[0]==end and r[1]==label and r[3]=='zone']
        if len(prices)==6:
            item_spreads.append({'item':label,'period':end,'zones_observed':6,
                                 'spread_percent':percentage(max(prices),min(prices))})
    expected['Q08_SPREAD_RANKING']=sorted(item_spreads,key=lambda x:(-x['spread_percent'],x['item']))[:params['top_n']]
    checks=[]
    for query_id,wanted in expected.items():
        actual=outputs[query_id]['rows']
        if len(actual)!=len(wanted): raise AssertionError(query_id+' row-count mismatch')
        for left,right in zip(actual,wanted):
            if left.keys()!=right.keys(): raise AssertionError(query_id+' column mismatch')
            for key,value in right.items():
                if isinstance(value,float):
                    # SQL operates on binary floats; the independent oracle uses Decimal.
                    if not math.isclose(left[key],value,abs_tol=0.01000001,rel_tol=0):
                        raise AssertionError(query_id+' numeric mismatch')
                elif left[key]!=value: raise AssertionError(query_id+' value mismatch')
        checks.append({'query':query_id,'rows_checked':len(wanted),'python_oracle_passed':True})
    return checks


def storage(con):
    payload={'page_count':con.execute('PRAGMA page_count').fetchone()[0],
             'page_size':con.execute('PRAGMA page_size').fetchone()[0],
             'freelist_count':con.execute('PRAGMA freelist_count').fetchone()[0],
             'indexes':[{'name':n,'sql':sql} for n,sql in con.execute(
                 "SELECT name,sql FROM sqlite_master WHERE type='index' ORDER BY name")]}
    try:
        payload['index_pages']=[{'name':n,'pages':pages,'bytes':size} for n,pages,size in con.execute(
            "SELECT name,count(*),sum(pgsize) FROM dbstat WHERE name LIKE 'idx_p2_%' GROUP BY name ORDER BY name")]
    except sqlite3.OperationalError:
        payload['index_pages']=None
    return payload


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def write_evidence(folder, report, outputs, plans):
    folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/'benchmark_results.json',report)
    write_json(folder/'query_results.json',outputs)
    write_json(folder/'execution_plans.json',plans)
    lines=['# Portfolio 2: Executed query results','',
           'Derived analytical results from NBS 2025 published averages. No raw price table is reproduced.',
           '',f"Focus item: {FOCUS_ITEM}. Focus geography: Nigeria. Run: {report['run_id']}.",'']
    for name,output in outputs.items():
        columns=output['columns']
        lines += ['## '+name,'','| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
        for row in output['rows']:
            lines.append('| '+' | '.join(str(row[col]).replace('|','\\|') for col in columns)+' |')
        lines.append('')
    (folder/'query_results.md').write_text('\n'.join(lines),encoding='utf-8')
    lines=['# Portfolio 2: Actual execution plans','',
           f"SQLite {report['environment']['sqlite_version']}. Plans are engine/version-specific. No plan hints were used.",'']
    for case in report['benchmarks']:
        lines += ['## '+case['case'],'']
        for phase in ('before','after'):
            lines += [phase.capitalize()+':','', '```text']
            lines += [f"{row['id']:3} parent={row['parent']:3}  {row['detail']}" for row in case['plans'][phase]]
            lines += ['```','']
    (folder/'execution_plans.md').write_text('\n'.join(lines),encoding='utf-8')


def run(source_path, workspace, evidence_dir=None, rounds=31, repetitions=200, warmups=20):
    if rounds<5 or repetitions<1 or warmups<1:
        raise ValueError('Use >=5 rounds, >=1 repetition and >=1 warm-up')
    source_path=source_path.resolve()
    if not source_path.is_file(): raise FileNotFoundError('Build Portfolio 1 first: '+str(source_path))
    if Path(str(source_path)+'-wal').exists():
        raise RuntimeError('Source has a WAL sidecar; close writers and checkpoint before benchmarking')
    original_hash=sha_file(source_path)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    local=workspace.resolve()/('portfolio2_'+run_id)
    local.mkdir(parents=True,exist_ok=False)
    with connection(source_path,readonly=True) as source:
        if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise AssertionError('Source integrity')
        if source.execute('PRAGMA foreign_key_check').fetchall(): raise AssertionError('Source foreign keys')
        if source.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'idx_p2_%'").fetchone()[0]:
            raise ValueError('Expected unmodified Portfolio 1 database without Portfolio 2 indexes')
        for label in ('baseline','optimised'):
            copy=connection(local/f'{label}.sqlite3')
            source.backup(copy)
            copy.close()
    source.close()
    baseline=connection(local/'baseline.sqlite3')
    tuned=connection(local/'optimised.sqlite3')
    try:
        baseline.execute('ANALYZE')
        baseline.commit()
        index_sql=(HERE/'indexes.sql').read_text(encoding='utf-8')
        start=perf_counter_ns()
        tuned.executescript(index_sql)
        setup_ms=(perf_counter_ns()-start)/1e6
        for con in (baseline,tuned):
            con.execute('PRAGMA query_only=ON')
        item_id=baseline.execute('SELECT item_id FROM item WHERE label=?',(FOCUS_ITEM,)).fetchone()[0]
        national_id=baseline.execute("SELECT geography_id FROM geography WHERE name='Nigeria'").fetchone()[0]
        params={'item_id':item_id,'item_text':str(item_id),'geography_id':national_id,'national_id':national_id,
                'start_period':'2025-01','end_period':'2025-12','floor_kobo':100000,'top_n':10}
        queries=sql_catalog('Queries')
        benchmark_queries=sql_catalog('Benchmark_Queries')
        outputs,plans={},{}
        for name,sql in queries.items():
            before=result(baseline,sql,params)
            after=result(tuned,sql,params)
            if before!=after: raise AssertionError(name+' changed after indexing')
            outputs[name]=after
            plans[name]={'before':explain(baseline,sql,params),'after':explain(tuned,sql,params)}
        correctness=independent_checks(baseline,outputs,params)
        cases=[('B01_series_lookup',(baseline,benchmark_queries['SERIES']),(tuned,benchmark_queries['SERIES'])),
               ('B02_top_prices',(baseline,benchmark_queries['TOP_PRICES']),(tuned,benchmark_queries['TOP_PRICES'])),
               ('B03_predicate_rewrite',(tuned,benchmark_queries['WRAPPED_SERIES']),(tuned,benchmark_queries['SERIES'])),
               ('B04_coverage_control',(baseline,queries['Q01_COVERAGE']),(tuned,queries['Q01_COVERAGE']))]
        measurements=[]
        raw_rows={}
        for name,before,after in cases:
            measured,rows=benchmark(name,before,after,params,rounds,repetitions,warmups)
            measurements.append(measured)
            raw_rows[name]=rows
            print(name,':',round(measured['before']['median_us'],3),'->',round(measured['after']['median_us'],3),
                  'microseconds; ratio',round(measured['before_over_after_ratio'],3),flush=True)
        if original_hash!=sha_file(source_path): raise AssertionError('Original database changed during experiment')
        for con in (baseline,tuned):
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise AssertionError('Copy integrity')
            if con.execute('PRAGMA foreign_key_check').fetchall(): raise AssertionError('Copy foreign keys')
        report={'run_id':run_id,'measured_at_utc':datetime.now(timezone.utc).isoformat(),
            'environment':{'python_version':sys.version.split()[0],'sqlite_version':sqlite3.sqlite_version,
                'os':platform.system()+' '+platform.release(),'machine':platform.machine(),'logical_cpus':os.cpu_count(),
                'sqlite_compile_options':[r[0] for r in baseline.execute('PRAGMA compile_options')],
                'settings':{name:baseline.execute('PRAGMA '+name).fetchone()[0]
                            for name in ('cache_size','temp_store','automatic_index','page_size','journal_mode','query_only')}},
            'source_database_sha256':original_hash,'source_unchanged':True,
            'source_observations':baseline.execute('SELECT count(*) FROM price_observation').fetchone()[0],
            'synthetic_observations':0,'parameters':params,'focus_item':FOCUS_ITEM,
            'protocol':{'rounds':rounds,'repetitions_per_round_per_side':repetitions,'warmups_per_side':warmups,
                        'alternating_order':True,'cache':'warm','timing_unit':'microseconds per execute + fetchall',
                        'sample_type':'mean of a batch; quartiles are not individual request latency percentiles',
                        'sqlite_progress_handler_interval':1},
            'tuned_index_creation_and_analyze_ms':setup_ms,
            'source_sql_sha256':{p.name:sha_file(p) for p in HERE.glob('*.sql')},
            'baseline_storage':storage(baseline),'tuned_storage':storage(tuned),
            'analytical_correctness_checks':correctness,'all_analytical_results_equal':True,
            'benchmarks':measurements}
        write_json(local/'raw_benchmark_rows_LOCAL_ONLY.json',raw_rows)
        destination=evidence_dir.resolve() if evidence_dir else local/'evidence'
        write_evidence(destination,report,outputs,plans)
        print('Evidence:',destination,flush=True)
        print('All eight analytical queries match independent Python checks; source database unchanged.',flush=True)
        return report
    finally:
        baseline.close()
        tuned.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=ROOT/'.local'/f'{PREFIX}_Food_Prices.sqlite3')
    parser.add_argument('--workspace',type=Path,default=ROOT/'.local')
    parser.add_argument('--evidence-dir',type=Path)
    parser.add_argument('--rounds',type=int,default=31)
    parser.add_argument('--repetitions',type=int,default=200)
    parser.add_argument('--warmups',type=int,default=20)
    args=parser.parse_args()
    run(args.database,args.workspace,args.evidence_dir,args.rounds,args.repetitions,args.warmups)


if __name__=='__main__': main()
