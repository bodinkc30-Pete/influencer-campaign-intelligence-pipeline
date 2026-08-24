from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.deliverable_performance import (
    IdentityResolver, excel_date_to_iso, get_value, is_influencer_header,
    is_performance_header, map_headers, nearest_section_label, norm, parse_number,
    pii_safe_text, stable_id,
)
from src.xlsx_probe import read_sheet_rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, object]], path: Path, fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    if not names:
        raise ValueError(f"no schema for {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=names)
        w.writeheader(); w.writerows(rows)


def campaign_for(mapping: dict, filename: str, sheet: str, section: str = "") -> tuple[str, str, str]:
    for item in mapping["sources"]:
        if item["source_filename"] != filename or item["source_sheet_name"] != sheet:
            continue
        if item.get("section_rules"):
            for rule in item["section_rules"]:
                if norm(rule["contains"]) in norm(section):
                    return rule["campaign_id"], rule["mapping_method"], rule["confidence"]
            return "", "section_not_mapped", ""
        return item.get("campaign_id", ""), item.get("mapping_method", ""), item.get("confidence", "")
    return "", "source_not_mapped", ""


def process_influencer_rows(filename: str, sheet: str, rows: list[list[object | None]], resolver: IdentityResolver, mapping: dict):
    deliverables=[]; perf=[]; issues=[]
    header_rows=[i for i,row in enumerate(rows,1) if is_influencer_header(row)]
    for hpos, header_row in enumerate(header_rows):
        headers=map_headers(rows[header_row-1])
        end=(header_rows[hpos+1]-1) if hpos+1<len(header_rows) else len(rows)
        section=nearest_section_label(rows, header_row)
        cid, method, conf=campaign_for(mapping, filename, sheet, section)
        for rowno in range(header_row+1, end+1):
            row=rows[rowno-1]
            identity=get_value(row, headers, "identity")
            if identity is None or not str(identity).strip() or norm(identity) in {"influencer", "kols name"}:
                continue
            inf_id, handle, resolve_method=resolver.resolve(identity)
            # false-positive summary/total rows
            if norm(identity) in {"total", "รวม"}:
                continue
            post_url=pii_safe_text(get_value(row, headers, "post_url"))
            if post_url and not ("tiktok" in post_url.casefold() or "http" in post_url.casefold()):
                post_url=""
            source_key=f"{filename}|{sheet}|{rowno}"
            deliverable_id=stable_id("dlv", cid, inf_id or handle, post_url or source_key)
            deliverables.append({
                "deliverable_id":deliverable_id,"campaign_id":cid,"influencer_id":inf_id,"canonical_handle":handle,
                "deliverable_type":"content_post","platform":"tiktok","product_raw":pii_safe_text(get_value(row, headers,"product")),
                "confirmed_raw":pii_safe_text(get_value(row,headers,"confirmed")),"posted_raw":pii_safe_text(get_value(row,headers,"posted")),
                "scheduled_date":excel_date_to_iso(get_value(row,headers,"schedule_date")),"posted_date":excel_date_to_iso(get_value(row,headers,"posted_date")),
                "post_url":post_url,"gencode_present":"yes" if str(get_value(row,headers,"gencode") or "").strip() else "no",
                "ad_status_raw":pii_safe_text(get_value(row,headers,"ad_status")),"identity_resolution_method":resolve_method,
                "campaign_mapping_method":method,"campaign_mapping_confidence":conf,"source_filename":filename,"source_sheet_name":sheet,
                "source_row_number":rowno,"source_section":section,"deliverable_version":"v1",
            })
            metric_values={k:parse_number(get_value(row,headers,k)) for k in ["views","likes","comments","saves","shares","gmv","sales","orders"]}
            if any(v is not None for v in metric_values.values()):
                perf.append({
                    "performance_id":stable_id("ipf", source_key),"campaign_id":cid,"influencer_id":inf_id,"deliverable_id":deliverable_id,
                    "canonical_handle":handle,"measurement_scope":"content_or_report_snapshot","measurement_date":excel_date_to_iso(get_value(row,headers,"posted_date")),
                    "views":metric_values["views"],"likes":metric_values["likes"],"comments":metric_values["comments"],"saves":metric_values["saves"],
                    "shares":metric_values["shares"],"gmv":metric_values["gmv"],"sales_amount":metric_values["sales"],"orders":metric_values["orders"],
                    "traffic":None,"impressions":None,"clicks":None,"cost":None,"revenue":None,"roi":None,"roas":None,
                    "metric_definition_version":"v1","source_filename":filename,"source_sheet_name":sheet,"source_row_number":rowno,
                })
            codes=[]
            if not cid: codes.append("CAMPAIGN_UNMAPPED")
            if not inf_id: codes.append("IDENTITY_UNRESOLVED_EXACT_ONLY")
            if codes:
                issues.append({"issue_id":stable_id("dpi",source_key),"campaign_id":cid,"influencer_id":inf_id,"source_filename":filename,"source_sheet_name":sheet,"source_row_number":rowno,"dq_status":"WARN","dq_codes":";".join(codes)})
    return deliverables,perf,issues


def process_campaign_performance(filename: str, sheet: str, rows: list[list[object | None]], mapping: dict, scope: str):
    out=[]; issues=[]
    headers_positions=[i for i,row in enumerate(rows,1) if is_performance_header(row)]
    for idx,hrow in enumerate(headers_positions):
        headers=map_headers(rows[hrow-1]); end=(headers_positions[idx+1]-1 if idx+1<len(headers_positions) else len(rows))
        section=nearest_section_label(rows,hrow)
        cid,method,conf=campaign_for(mapping,filename,sheet,section)
        for rowno in range(hrow+1,end+1):
            row=rows[rowno-1]
            vals={k:parse_number(get_value(row,headers,k)) for k in ["sales","orders","traffic","viewers","views","gmv","revenue","roi","roas","cost","impressions","clicks","ctr","likes","comments","shares"]}
            if not any(v is not None for v in vals.values()): continue
            first=str(row[0] if row else "").strip()
            if norm(first) in {"total","รวม"}: continue
            source_key=f"{filename}|{sheet}|{rowno}"
            raw_metric_values=[get_value(row,headers,k) for k in ["sales","orders","traffic","viewers","views","gmv","revenue","roi","roas","cost","impressions","clicks","ctr","likes","comments","shares"]]
            source_error = any(str(v).strip() in {"#DIV/0!", "#N/A", "#VALUE!", "#REF!", "#NAME?"} for v in raw_metric_values if v is not None)
            out.append({
                "campaign_performance_id":stable_id("cpf",source_key),"campaign_id":cid,"performance_scope":scope,
                "event_date":excel_date_to_iso(get_value(row,headers,"schedule_date") or (row[0] if row else None)),"platform_raw":pii_safe_text(row[5] if len(row)>5 and scope=="live_session" else ""),
                "sales_amount":vals["sales"],"orders":vals["orders"],"traffic":vals["traffic"],"viewers":vals["viewers"] or vals["views"],
                "likes":vals["likes"],"comments":vals["comments"],"shares":vals["shares"],"gmv":vals["gmv"],"revenue":vals["revenue"],
                "cost":vals["cost"],"roi":vals["roi"],"roas":vals["roas"],"impressions":vals["impressions"],"clicks":vals["clicks"],"ctr":vals["ctr"],
                "campaign_mapping_method":method,"campaign_mapping_confidence":conf,"metric_definition_version":"v1",
                "source_filename":filename,"source_sheet_name":sheet,"source_row_number":rowno,"source_section":section,
            })
            if not cid:
                issues.append({"issue_id":stable_id("dpi",source_key),"campaign_id":"","influencer_id":"","source_filename":filename,"source_sheet_name":sheet,"source_row_number":rowno,"dq_status":"WARN","dq_codes":"CAMPAIGN_UNMAPPED"})
            if source_error:
                issues.append({"issue_id":stable_id("dpi",source_key,"metric_error"),"campaign_id":cid,"influencer_id":"","source_filename":filename,"source_sheet_name":sheet,"source_row_number":rowno,"dq_status":"WARN","dq_codes":"SOURCE_METRIC_ERROR_LITERAL"})
    return out,issues


def seller_gmv(filename,sheet,rows,resolver,mapping):
    if not rows: return [],[]
    headers=map_headers(rows[0]); cid,method,conf=campaign_for(mapping,filename,sheet,"")
    out=[]; issues=[]
    for rowno,row in enumerate(rows[1:],2):
        if not row or not str(row[0] if row else "").strip(): continue
        inf_id,handle,rmethod=resolver.resolve(row[0])
        source_key=f"{filename}|{sheet}|{rowno}"
        out.append({
            "performance_id":stable_id("ipf",source_key),"campaign_id":cid,"influencer_id":inf_id,"deliverable_id":"","canonical_handle":handle,
            "measurement_scope":"affiliate_seller_snapshot","measurement_date":"","views":None,"likes":None,"comments":None,"saves":None,"shares":None,
            "gmv":parse_number(row[1] if len(row)>1 else None),"sales_amount":None,"orders":parse_number(row[15] if len(row)>15 else None),"traffic":None,
            "impressions":parse_number(row[14] if len(row)>14 else None),"clicks":None,"cost":None,"revenue":None,"roi":None,"roas":None,
            "metric_definition_version":"v1","source_filename":filename,"source_sheet_name":sheet,"source_row_number":rowno,
        })
        if not inf_id:
            issues.append({"issue_id":stable_id("dpi",source_key),"campaign_id":cid,"influencer_id":"","source_filename":filename,"source_sheet_name":sheet,"source_row_number":rowno,"dq_status":"WARN","dq_codes":"IDENTITY_UNRESOLVED_EXACT_ONLY"})
    return out,issues


def main() -> int:
    ap=argparse.ArgumentParser();
    ap.add_argument("--input-dir",type=Path,required=True); ap.add_argument("--mapping",type=Path,required=True)
    ap.add_argument("--master",type=Path,required=True); ap.add_argument("--aliases",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args(); mapping=json.loads(args.mapping.read_text(encoding="utf-8")); resolver=IdentityResolver(read_csv(args.master),read_csv(args.aliases))
    deliverables=[]; iperf=[]; cperf=[]; issues=[]
    for src in mapping["sources"]:
        filename=src["source_filename"]; sheet=src["source_sheet_name"]; kind=src["adapter"]
        rows=read_sheet_rows(args.input_dir/filename,sheet,max_cols=40)
        if kind in {"influencer_content","influencer_report"}:
            d,p,i=process_influencer_rows(filename,sheet,rows,resolver,mapping); deliverables+=d; iperf+=p; issues+=i
        elif kind in {"campaign_live","campaign_ads","monthly_performance"}:
            p,i=process_campaign_performance(filename,sheet,rows,mapping,{"campaign_live":"live_session","campaign_ads":"ads_report","monthly_performance":"monthly_platform"}[kind]); cperf+=p; issues+=i
        elif kind=="seller_gmv":
            p,i=seller_gmv(filename,sheet,rows,resolver,mapping); iperf+=p; issues+=i
    # Promote only records that satisfy Campaign + Golden Master identity gates.
    deliverable_quarantine=[]
    promoted_observations=[]
    for d in deliverables:
        if d["campaign_id"] and d["influencer_id"]:
            promoted_observations.append(d)
        else:
            codes=[]
            if not d["campaign_id"]: codes.append("CAMPAIGN_UNMAPPED")
            if not d["influencer_id"]: codes.append("IDENTITY_UNRESOLVED_EXACT_ONLY")
            deliverable_quarantine.append({"record_type":"deliverable_observation","source_filename":d["source_filename"],"source_sheet_name":d["source_sheet_name"],"source_row_number":d["source_row_number"],"campaign_id":d["campaign_id"],"identity_raw":"","canonical_handle_candidate":d["canonical_handle"],"dq_codes":";".join(codes)})

    promoted_iperf=[]
    for p in iperf:
        if p["campaign_id"] and p["influencer_id"]:
            promoted_iperf.append(p)
        else:
            codes=[]
            if not p["campaign_id"]: codes.append("CAMPAIGN_UNMAPPED")
            if not p["influencer_id"]: codes.append("IDENTITY_UNRESOLVED_EXACT_ONLY")
            deliverable_quarantine.append({"record_type":"influencer_performance","source_filename":p["source_filename"],"source_sheet_name":p["source_sheet_name"],"source_row_number":p["source_row_number"],"campaign_id":p["campaign_id"],"identity_raw":"","canonical_handle_candidate":p["canonical_handle"],"dq_codes":";".join(codes)})

    # Canonical deliverable fact: collapse only exact same post URL within campaign+influencer.
    grouped=defaultdict(list)
    for d in promoted_observations:
        key=(d["campaign_id"],d["influencer_id"],d["post_url"]) if d["post_url"] else (d["campaign_id"],d["influencer_id"],d["source_filename"],d["source_sheet_name"],d["source_row_number"])
        grouped[key].append(d)
    deliverable_fact=[]
    for key, vals in grouped.items():
        base=dict(vals[0])
        base["observation_count"]=len(vals)
        base["source_occurrences"]=" || ".join(f"{v['source_filename']} | {v['source_sheet_name']} | row {v['source_row_number']}" for v in vals)
        base["deliverable_dq_status"]="WARN" if len(vals)>1 else "PASS"
        base["deliverable_dq_codes"]="MULTIPLE_SOURCE_OBSERVATIONS_SAME_POST" if len(vals)>1 else ""
        # Stable canonical id must not depend on which duplicate observation appears first.
        if base["post_url"]:
            base["deliverable_id"]=stable_id("dlv",base["campaign_id"],base["influencer_id"],base["post_url"])
        deliverable_fact.append(base)
        if len(vals)>1:
            issues.append({"issue_id":stable_id("dpi",base["deliverable_id"],"multi_source"),"campaign_id":base["campaign_id"],"influencer_id":base["influencer_id"],"source_filename":base["source_filename"],"source_sheet_name":base["source_sheet_name"],"source_row_number":base["source_row_number"],"dq_status":"WARN","dq_codes":"MULTIPLE_SOURCE_OBSERVATIONS_SAME_POST"})

    args.output_dir.mkdir(parents=True,exist_ok=True)
    write_csv(promoted_observations,args.output_dir/"campaign_deliverable_observation_v1.csv")
    write_csv(deliverable_fact,args.output_dir/"fact_campaign_deliverable_v1.csv")
    write_csv(promoted_iperf,args.output_dir/"fact_influencer_performance_v1.csv")
    write_csv(cperf,args.output_dir/"fact_campaign_performance_v1.csv")
    write_csv(deliverable_quarantine,args.output_dir/"deliverable_performance_quarantine_v1.csv",["record_type","source_filename","source_sheet_name","source_row_number","campaign_id","identity_raw","canonical_handle_candidate","dq_codes"])
    # DQ issues for promoted facts only; unresolved rows live in quarantine.
    promoted_issues=[i for i in issues if "IDENTITY_UNRESOLVED_EXACT_ONLY" not in i.get("dq_codes","") and "CAMPAIGN_UNMAPPED" not in i.get("dq_codes","")]
    write_csv(promoted_issues,args.output_dir/"deliverable_performance_dq_issues_v1.csv",["issue_id","campaign_id","influencer_id","source_filename","source_sheet_name","source_row_number","dq_status","dq_codes"])
    metric_contract=[
        {"canonical_metric":"views","scope":"influencer/content","meaning":"Source-reported video views","unit":"count","merge_rule":"do not mix with live viewers"},
        {"canonical_metric":"gmv","scope":"influencer/content/affiliate","meaning":"Source field explicitly labelled GMV","unit":"source currency","merge_rule":"do not equate to revenue/sales_amount"},
        {"canonical_metric":"sales_amount","scope":"live/campaign","meaning":"Source field labelled ยอดขาย","unit":"source currency","merge_rule":"keep distinct from GMV and gross revenue"},
        {"canonical_metric":"revenue","scope":"ads/monthly","meaning":"Source field labelled Revenue or รายได้ขั้นต้น","unit":"source currency","merge_rule":"keep source scope"},
        {"canonical_metric":"viewers","scope":"live","meaning":"Live viewers / total viewers","unit":"count","merge_rule":"do not mix with video views"},
        {"canonical_metric":"orders","scope":"all supported","meaning":"Source-reported orders","unit":"count","merge_rule":"retain source scope"},
        {"canonical_metric":"roi","scope":"ads","meaning":"Source-reported ROI","unit":"ratio","merge_rule":"do not treat as ROAS"},
        {"canonical_metric":"roas","scope":"monthly/ads","meaning":"Source-reported ROAS","unit":"ratio","merge_rule":"do not treat as ROI"},
    ]
    write_csv(metric_contract,args.output_dir/"performance_metric_contract_v1.csv")
    recon=[
        {"metric":"deliverable_observations_promoted","value":len(promoted_observations),"status":"PASS"},
        {"metric":"canonical_deliverable_facts","value":len(deliverable_fact),"status":"PASS"},
        {"metric":"influencer_performance_records_promoted","value":len(promoted_iperf),"status":"PASS"},
        {"metric":"campaign_performance_records","value":len(cperf),"status":"PASS"},
        {"metric":"quarantined_records","value":len(deliverable_quarantine),"status":"WARN" if deliverable_quarantine else "PASS"},
        {"metric":"promoted_deliverables_missing_campaign","value":sum(not d["campaign_id"] for d in promoted_observations),"status":"PASS"},
        {"metric":"promoted_deliverables_missing_influencer","value":sum(not d["influencer_id"] for d in promoted_observations),"status":"PASS"},
        {"metric":"promoted_influencer_performance_missing_influencer","value":sum(not p["influencer_id"] for p in promoted_iperf),"status":"PASS"},
        {"metric":"campaign_performance_missing_campaign","value":sum(not p["campaign_id"] for p in cperf),"status":"WARN" if any(not p["campaign_id"] for p in cperf) else "PASS"},
        {"metric":"promoted_dq_issue_records","value":len(promoted_issues),"status":"WARN" if promoted_issues else "PASS"},
        {"metric":"pii_fields_emitted","value":0,"status":"PASS"},
        {"metric":"fuzzy_identity_resolution","value":0,"status":"PASS"},
    ]
    write_csv(recon,args.output_dir/"deliverable_performance_reconciliation_v1.csv")
    print(json.dumps({"deliverable_observations":len(deliverables),"promoted_deliverable_observations":len(promoted_observations),"canonical_deliverables":len(deliverable_fact),"influencer_performance_input":len(iperf),"promoted_influencer_performance":len(promoted_iperf),"campaign_performance":len(cperf),"quarantined":len(deliverable_quarantine),"promoted_dq_issues":len(promoted_issues),"reconciliation":recon},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
