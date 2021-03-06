import sys
import xml.etree.ElementTree as ET
import argparse
import ConfigParser
import httplib, urllib
import codecs
import os


import logging
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
    pubmed_api_key=parameters['pubmed_api_key']
    if not os.path.exists(gold_answer_folder):
        os.makedirs(gold_answer_folder)
    download_goldanswer(pubmed_search_query, gold_anwser_file_classifier_format, gold_answer_classification_label,  pubmed_api_key, gold_answer_quantity_to_retrieve)
    
    
    
def ReadParameters(args):
    if(args.p!=None):
        Config = ConfigParser.ConfigParser()
        Config.read(args.p)
        parameters['gold_answer_folder']=Config.get('MAIN', 'gold_answer_folder')
        parameters['pubmed_search_query']=Config.get('MAIN', 'pubmed_search_query')
        parameters['gold_anwser_file_classifier_format']=Config.get('MAIN', 'gold_anwser_file_classifier_format')
        parameters['gold_answer_classification_label']=Config.get('MAIN', 'gold_answer_classification_label')
        parameters['gold_answer_quantity_to_retrieve']=Config.get('MAIN', 'gold_answer_quantity_to_retrieve')
        parameters['pubmed_api_key']=Config.get('MAIN', 'pubmed_api_key')
    else:
        logging.error("Please send the correct parameters config.properties --help ")
        sys.exit(1)
    return parameters   


def download_goldanswer(pubmed_search_query, pubmed_result_output, classification_token, pubmed_api_key, retmax=50000):
    logging.info("Downloading Gold Answer Query : " + pubmed_search_query + ".  Retmax : "  + retmax)
    params = urllib.urlencode({'db':'pubmed','rettype':'xml','retmode':'xml','term': pubmed_search_query, 'retmax':str(retmax)})
    conn = httplib.HTTPSConnection("eutils.ncbi.nlm.nih.gov")
    conn.request("POST", "/entrez/eutils/esearch.fcgi", params )
    rpub = conn.getresponse()
    if not rpub.status == 200 :
        logging.error("Error en la conexion:   "  + rpub.status + " " + rpub.reason)
        exit()
    response_pubmed = rpub.read()
    docXml = ET.fromstring(response_pubmed)
    with open(pubmed_result_output+"_id_list.txt",'w') as pmid_list_file: 
        with codecs.open(pubmed_result_output,'w',encoding='utf8') as txt_file:
            for f in docXml.find("IdList").findall("Id") :
                try:
                    #time.sleep(0.1)  
                    #to do add &sort=relevance as a parameter
                    params = urllib.urlencode({'db':'pubmed','retmode':'xml','id':f.text,'sort':'relevance','api_key':pubmed_api_key})
                    #params = urllib.urlencode({'db':'pubmed','retmode':'xml','id':'23424122','api_key':pubmed_api_key})
                    
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
                        abstract = readAbstract(abstract_xml)
                        if(abstract!=''):
                            title_xml=article_xml.find("ArticleTitle")
                            title = readTitle(title_xml)
                            if(title!=""):
                                art_txt = art_txt + remove_invalid_characters(title) + "\t" 
                            else:
                                art_txt = art_txt + " " + "\t"     
                            abstract_xml = article_xml.find("Abstract")
                            art_txt = art_txt + remove_invalid_characters(abstract) + "\n"
                            data=art_txt.split('\t')
                            if(len(data)==4):
                                txt_file.write(art_txt)
                                txt_file.flush()
                                pmid_list_file.write(pmid+"\n")
                                pmid_list_file.flush()
                            else:
                                logging.error("Error Downloading  " + pmid + ". The document does not have a well tabulation format. The line: ")
                                logging.error(art_txt)
                    rf.close()
                    conn2.close()
                except Exception as inst:
                    logging.error("Error Downloading  " + f.text )
            txt_file.close()
        pmid_list_file.close()        
    rpub.close()
    conn.close()         
    logging.info("Download End ")  


def readTitle(title_xml):
    if(title_xml!=None):
        title=''.join(itertext_title(title_xml))
        return title
    return ''
def readAbstract(abstract_xml):
    if(abstract_xml!=None):
        abstract = ''.join(itertext_abstract(abstract_xml))
        return abstract 
    return ''
def itertext_title(self):
    tag = self.tag
    if not isinstance(tag, str) and tag is not None:
        return
    if self.text:
        yield self.text.strip()
    for e in self:
        for s in e.itertext():
            yield s.strip()
        if e.tail:
            yield e.tail.strip()
            
def itertext_abstract(self):
    tag = self.tag
    if not isinstance(tag, str) and tag is not None:
        return
    if self.text:
        yield self.text.strip()
        for e in self:
            tag2=e.tag
            if isinstance(tag2, str) and tag2 is not None and tag2 in ['AbstractText']: 
                for s in e.itertext():
                    yield s.strip()
                if e.tail:
                    yield e.tail.strip()
            elif tag2 not in ['CopyrightInformation']:
                print tag2        
    else:
        print "no text"            

def remove_invalid_characters(text):
    text = text.replace("\n"," ").replace("\t"," ").replace("\r"," ")    
    return text
