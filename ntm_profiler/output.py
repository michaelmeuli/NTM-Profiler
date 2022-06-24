
from collections import defaultdict
import os
from pathogenprofiler import filecheck, debug, infolog
import csv
import pathogenprofiler as pp
import time
from tqdm import tqdm
import json

def write_outputs(args,results):
    infolog("\nWriting outputs")
    infolog("---------------")
    json_output = args.dir+"/"+args.prefix+".results.json"
    text_output = args.dir+"/"+args.prefix+".results.txt"
    csv_output = args.dir+"/"+args.prefix+".results.csv"
    extra_columns = [x.lower() for x in args.add_columns.split(",")] if args.add_columns else []
    infolog(f"Writing json file: {json_output}")
    json.dump(results,open(json_output,"w"))
    if args.txt:
        infolog(f"Writing text file: {text_output}")
        write_text(results,args.conf,text_output,extra_columns,reporting_af=args.reporting_af)
    if args.csv:
        infolog(f"Writing csv file: {csv_output}")
        write_text(results,args.conf,csv_output,extra_columns)

        
def load_text(text_strings):
    text = """
NTM-Profiler report
=================

The following report has been generated by NTM-Profiler.

Summary
-------
ID%(sep)s%(id)s
Date%(sep)s%(date)s
""" % text_strings
    if "species_report" in text_strings:
        text+="""
Species report
-----------------
%(species_report)s
""" % text_strings
    if "mash_species_report" in text_strings:
        text+="""
Mash species report
-----------------
%(mash_species_report)s
""" % text_strings
    if "cluster_report" in text_strings:
        text+="""
Cluster report
-----------------
%(cluster_report)s
""" % text_strings
    if "dr_report" in text_strings:
        text+="""
Resistance report
-----------------
%(dr_report)s
""" % text_strings
    if "dr_genes_report" in text_strings:
        text+="""
Resistance genes report
-----------------
%(dr_genes_report)s
""" % text_strings
    text += """
Resistance variants report
-----------------
%(dr_var_report)s

Other variants report
---------------------
%(other_var_report)s

Coverage report
---------------------
%(coverage_report)s

Missing positions report
---------------------
%(missing_report)s

Analysis pipeline specifications
--------------------------------
Pipeline version%(sep)s%(version)s
Species Database version%(sep)s%(species_db_version)s
Resistance Database version%(sep)s%(resistance_db_version)s

%(pipeline)s
""" % text_strings
    return text

def load_species_text(text_strings):
    text = r"""
NTM-Profiler report
=================

The following report has been generated by NTM-Profiler.

Summary
-------
ID%(sep)s%(id)s
Date%(sep)s%(date)s

Species report
-----------------
%(species_report)s""" % text_strings
    if "mash_species_report" in text_strings:
        text+="""
Mash species report
-----------------
%(mash_species_report)s
""" % text_strings
    text += """
Analysis pipeline specifications
--------------------------------
Pipeline version%(sep)s%(version)s
Species Database version%(sep)s%(species_db_version)s

%(pipeline)s
""" % text_strings
    return text

def write_text(json_results,conf,outfile,columns = None,reporting_af = 0.0,sep="\t"):
    if "resistance_genes" not in json_results:
        return write_species_text(json_results,outfile)
    json_results = pp.get_summary(json_results,conf,columns = columns,reporting_af=reporting_af)
    json_results["drug_table"] = [[y for y in json_results["drug_table"] if y["Drug"].upper()==d.upper()][0] for d in conf["drugs"]]
    for var in json_results["dr_variants"]:
        var["drug"] = ", ".join([d["drug"] for d in var["drugs"]])
    text_strings = {}
    text_strings["id"] = json_results["id"]
    text_strings["date"] = time.ctime()
    if json_results["species"] is not None:
        text_strings["species_report"] = pp.dict_list2text(json_results["species"]["prediction"],["species","mean"],{"species":"Species","mean":"Mean kmer coverage"},sep=sep)
    text_strings["cluster_report"] = pp.dict_list2text(json_results["barcode"],mappings={"annotation":"Cluster","freq":"Frequency"})
    text_strings["dr_report"] = pp.dict_list2text(json_results["drug_table"],["Drug","Genotypic Resistance","Mutations"]+columns if columns else [],sep=sep)
    text_strings["dr_genes_report"] = pp.dict_list2text(json_results["resistance_genes"],mappings={"locus_tag":"Locus Tag","gene":"Gene","drugs.drug":"Drug"},sep=sep)
    text_strings["dr_var_report"] = pp.dict_list2text(json_results["dr_variants"],mappings={"genome_pos":"Genome Position","locus_tag":"Locus Tag","type":"Variant type","change":"Change","freq":"Estimated fraction","drugs.drug":"Drug"},sep=sep)
    text_strings["other_var_report"] = pp.dict_list2text(json_results["other_variants"],mappings={"genome_pos":"Genome Position","locus_tag":"Locus Tag","type":"Variant type","change":"Change","freq":"Estimated fraction"},sep=sep)
    text_strings["coverage_report"] = pp.dict_list2text(json_results["qc"]["gene_coverage"], ["gene","locus_tag","cutoff","fraction"],sep=sep) if "gene_coverage" in json_results["qc"] else "N/A"
    text_strings["missing_report"] = pp.dict_list2text(json_results["qc"]["missing_positions"],["gene","locus_tag","position","position_type","drug_resistance_position"],sep=sep) if "missing_report" in json_results["qc"] else "N/A"
    text_strings["pipeline"] = pp.dict_list2text(json_results["pipeline_software"],["Analysis","Program"],sep=sep)
    text_strings["version"] = json_results["software_version"]
    text_strings["species_db_version"] = "%(name)s_%(commit)s_%(Author)s_%(Date)s" % json_results["species"]["species_db_version"] if "species_db_version" in json_results else "N/A"
    text_strings["resistance_db_version"] = "%(name)s_%(commit)s_%(Author)s_%(Date)s" % json_results["resistance_db_version"] if "resistance_db_version" in json_results else "N/A"
    if sep=="\t":
        text_strings["sep"] = ": "
    else:
        text_strings["sep"] = ","

    o = open(outfile,"w")
    o.write(load_text(text_strings))
    o.close()


def write_species_text(json_results,outfile,sep="\t"):
    text_strings = {}
    text_strings["id"] = json_results["id"]
    text_strings["date"] = time.ctime()
    text_strings["species_report"] = pp.dict_list2text(json_results["species"]["prediction"],["species","mean"],{"species":"Species","mean":"Mean kmer coverage"},sep=sep)
    if "mash_closest_species" in json_results:
        text_strings["mash_species_report"] = pp.dict_list2text(json_results["mash_closest_species"]["prediction"],{"accession":"Accession","species":"Species","mash-ANI":"mash-ANI"},sep=sep)
    text_strings["pipeline"] = pp.dict_list2text(json_results["pipeline_software"],["Analysis","Program"],sep=sep)
    text_strings["version"] = json_results["software_version"]
    text_strings["species_db_version"] = "%(name)s_%(commit)s_%(Author)s_%(Date)s" % json_results["species"]["species_db_version"]
    if sep=="\t":
        text_strings["sep"] = ": "
    else:
        text_strings["sep"] = ","
    with open(outfile,"w") as O:
        O.write(load_species_text(text_strings))





def collate(args):
    # Get a dictionary with the database file: {"ref": "/path/to/fasta" ... etc. }
    
    if args.samples:
        samples = [x.rstrip() for x in open(args.samples).readlines()]
    else:
        samples = [x.replace(args.suffix,"") for x in os.listdir(args.dir) if x[-len(args.suffix):]==args.suffix]

    if len(samples)==0:
        pp.infolog(f"\nNo result files found in directory '{args.dir}'. Do you need to specify '--dir'?\n")
        quit(0)

    # Loop through the sample result files    
    species = {}
    dr = defaultdict(lambda: defaultdict(list))
    drugs = set()
    dr_samples = set()
    closest_seq = {}
    barcode = {}
    for s in tqdm(samples):
        # Data has the same structure as the .result.json files
        data = json.load(open(filecheck("%s/%s%s" % (args.dir,s,args.suffix))))
        if len(data["species"]["prediction"])>0:
            species[s] = ";".join([d["species"] for d in data["species"]["prediction"]])
        if "mash_closest_species" in data:
            closest_seq[s] = "|".join(pp.stringify(data["mash_closest_species"]["prediction"][0].values()))
        if "barcode" in data:
            barcode[s] = "|".join(pp.stringify([x["annotation"] for x in data["barcode"]]))
        if "resistance_db_version" in data:
            dr_samples.add(s)
            for gene in data["resistance_genes"]:
                for d in gene["drugs"]:
                    drugs.add(d["drug"])
                    dr[s][d["drug"]].append(f"{gene['gene']}_resistance_gene")
        
            for var in data["dr_variants"]:
                for d in var["drugs"]:
                    drugs.add(d["drug"])
                    dr[s][d["drug"]].append(f"{var['gene']}_{var['change']}")

    results = []
    for s in samples:
        result = {
            "id": s,
            "species": species.get(s,"N/A"),
            "closest-sequence": closest_seq.get(s,"N/A")
        }
        if len(barcode)>0:
            result["barcode"] = barcode.get(s,"N/A")
        for d in sorted(drugs):
            if s in dr_samples:
                if d in dr[s]:
                    result[d] = ";".join(dr[s][d])
                else:
                    result[d] = ""
            else:
                result[d] = "N/A"
        results.append(result)
    
    if args.format=="txt":
        args.sep = "\t"
    else:
        args.sep = ","

    with open(args.outfile,"w") as O:
        writer = csv.DictWriter(O,fieldnames=list(results[0]),delimiter=args.sep)
        writer.writeheader()
        writer.writerows(results)
