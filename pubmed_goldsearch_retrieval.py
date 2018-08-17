import sys
import xml.etree.ElementTree as ET
import argparse
import ConfigParser
import httplib, urllib
import codecs
import os
import logging
import time

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

parser=argparse.ArgumentParser()
parser.add_argument('-p', help='Path Parameters')
args=parser.parse_args()
parameters={}
if __name__ == '__main__':
    import pubmed_goldsearch_retrieval
    parameters = pubmed_goldsearch_retrieval.ReadParameters(args)     
    pubmed_goldsearch_retrieval.Main(parameters)

def Main(parameters):
    gold_answer_folder=parameters['gold_answer_folder']
    pubmed_search_query= parameters['pubmed_search_query']
    gold_anwser_file_classifier_format=parameters['gold_anwser_file_classifier_format']
    gold_answer_quantity_to_retrieve=parameters['gold_answer_quantity_to_retrieve']
    gold_answer_classification_label=parameters['gold_answer_classification_label']
    if not os.path.exists(gold_answer_folder):
        os.makedirs(gold_answer_folder)
    download_goldanswer(pubmed_search_query, gold_anwser_file_classifier_format, gold_answer_classification_label, gold_answer_quantity_to_retrieve)
    
    
    
def ReadParameters(args):
    if(args.p!=None):
        Config = ConfigParser.ConfigParser()
        Config.read(args.p)
        parameters['gold_answer_folder']=Config.get('MAIN', 'gold_answer_folder')
        parameters['pubmed_search_query']=Config.get('MAIN', 'pubmed_search_query')
        parameters['gold_anwser_file_classifier_format']=Config.get('MAIN', 'gold_anwser_file_classifier_format')
        parameters['gold_answer_classification_label']=Config.get('MAIN', 'gold_answer_classification_label')
        parameters['gold_answer_quantity_to_retrieve']=Config.get('MAIN', 'gold_answer_quantity_to_retrieve')
    else:
        logging.error("Please send the correct parameters config.properties --help ")
        sys.exit(1)
    return parameters   


def download_goldanswer(pubmed_search_query, pubmed_result_output, classification_token, retmax=50000):   
    logging.info("Downloading Gold Answer Query : " + pubmed_search_query + ".  Retmax : "  + retmax)
    params = urllib.urlencode({'db':'pubmed','rettype':'xml','retmode':'xml','term': pubmed_search_query, 'retmax':str(retmax)})
    conn = httplib.HTTPSConnection("eutils.ncbi.nlm.nih.gov")
    conn.request("POST", "/entrez/eutils/esearch.fcgi", params )
    rpub = conn.getresponse()
    if not rpub.status == 200 :
        print "Error en la conexion: " + rpub.status + " " + rpub.reason 
        exit()
    response_pubmed = rpub.read()
    docXml = ET.fromstring(response_pubmed)
    with open(pubmed_result_output+"_id_list.txt",'w') as pmid_list_file: 
        with codecs.open(pubmed_result_output,'w',encoding='utf8') as txt_file:
            for f in docXml.find("IdList").findall("Id") :
                try:
                    time.sleep(0.1)  
                    params = urllib.urlencode({'db':'pubmed','retmode':'xml','id':f.text})
                    conn2 = httplib.HTTPSConnection("eutils.ncbi.nlm.nih.gov")
                    conn2.request("POST", "/entrez/eutils/efetch.fcgi", params )
                    rf = conn2.getresponse()
                    if not rf.status == 200 :
                        logging.error("Error en la conexion:   "  + rf.status + " " + rf.reason)
                        exit()
                    response_efetch = rf.read()
                    docXml_E = ET.fromstring(response_efetch) 
                    article = docXml_E.find("PubmedArticle")
                    if(article!=None):
                        pmid = article.find("MedlineCitation").find("PMID").text
                        art_txt = classification_token + "\t" + pmid + "\t"    
                        article_xml = article.find("MedlineCitation").find("Article")
                        abstract_xml = article_xml.find("Abstract")
                        if(abstract_xml!=None):
                            title_xml=article_xml.find("ArticleTitle")
                            if(title_xml!=None):
                                title = title_xml.text
                                if(title!=None):
                                    art_txt = art_txt + title.replace("\n"," ").replace("\t"," ").replace("\r"," ") + "\t" 
                                else:
                                    art_txt = art_txt + " " + "\t"     
                                abstract_xml = article_xml.find("Abstract")
                                if(abstract_xml!=None):
                                    abstract_text = abstract_xml.find("AbstractText")
                                    if(abstract_text!=None):
                                        abstract=abstract_text.text
                                        if(abstract!=None):
                                            art_txt = art_txt + abstract.replace("\n"," ").replace("\t"," ").replace("\r"," ") + "\n" 
                                            txt_file.write(art_txt)
                                            txt_file.flush()
                                            pmid_list_file.write(pmid+"\n")
                                            pmid_list_file.flush()   
                    rf.close
                    conn2.close()
                except Exception as inst:
                    logging.error("Error Downloading  " )
                    logging.error("Error Downloading  " + inst)    
            txt_file.close()
        pmid_list_file.close()        
    rpub.close
    conn.close()         
    logging.info("Download End ")    


