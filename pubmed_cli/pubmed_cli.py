import argparse
import csv
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

# Constants for PubMed API
PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# List of known pharmaceutical and biotech company keywords
COMPANY_KEYWORDS = ["pharma", "biotech", "therapeutics", "biosciences", "lifesciences", "laboratories", "inc", "corp", "llc"]

def fetch_pubmed_papers(query: str, debug: bool = False) -> List[Dict[str, str]]:
    """
    Fetches research papers from PubMed based on a user query.
    """
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 10,  # Fetch 10 results for testing; can be increased
    }
    response = requests.get(PUBMED_API_URL, params=params)
    if debug:
        print(f"Querying PubMed API: {response.url}")
    
    if response.status_code != 200:
        print("Error fetching data from PubMed API")
        return []
    
    result = response.json()
    paper_ids = result.get("esearchresult", {}).get("idlist", [])
    
    return fetch_paper_details(paper_ids, debug)


def fetch_paper_details(paper_ids: List[str], debug: bool = False) -> List[Dict[str, str]]:
    """
    Fetches detailed information for given PubMed paper IDs.
    """
    if not paper_ids:
        return []
    
    params = {
        "db": "pubmed",
        "id": ",".join(paper_ids),
        "retmode": "xml",
    }
    response = requests.get(PUBMED_FETCH_URL, params=params)
    if debug:
        print(f"Fetching details for papers: {response.url}")
    
    if response.status_code != 200:
        print("Error fetching paper details from PubMed API")
        return []
    
    return parse_pubmed_xml(response.text, debug)


def parse_pubmed_xml(xml_data: str, debug: bool = False) -> List[Dict[str, str]]:
    """
    Parses the XML response from PubMed and extracts required fields.
    """
    root = ET.fromstring(xml_data)
    papers = []
    
    for article in root.findall(".//PubmedArticle"):
        pubmed_id = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle")
        pub_date = article.findtext(".//PubDate/Year")
        
        authors = []
        affiliations = []
        company_affiliations = []
        email = ""
        
        for author in article.findall(".//Author"):
            last_name = author.findtext("LastName", "")
            fore_name = author.findtext("ForeName", "")
            full_name = f"{fore_name} {last_name}".strip()
            if full_name:
                authors.append(full_name)
            
            aff = author.findtext(".//Affiliation", "")
            if aff:
                affiliations.append(aff)
                if any(keyword.lower() in aff.lower() for keyword in COMPANY_KEYWORDS):
                    company_affiliations.append(aff)
                if "@" in aff:
                    email = aff  # Extract corresponding author email if found
        
        if company_affiliations:  # Only include papers with company affiliations
            papers.append({
                "PubmedID": pubmed_id,
                "Title": title,
                "Publication Date": pub_date,
                "Non-academic Authors": ", ".join(authors),
                "Company Affiliations": ", ".join(company_affiliations),
                "Corresponding Author Email": email,
            })
    
    if debug:
        print(f"Parsed {len(papers)} papers from XML data")
    
    return papers


def save_to_csv(filename: str, papers: List[Dict[str, str]]):
    """
    Saves research paper details to a CSV file.
    """
    fieldnames = ["PubmedID", "Title", "Publication Date", "Non-academic Authors", "Company Affiliations", "Corresponding Author Email"]
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)
    print(f"Results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Fetch research papers from PubMed based on a user query.")
    parser.add_argument("query", type=str, help="Search query for PubMed")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-f", "--file", type=str, help="Filename to save results as CSV")
    args = parser.parse_args()
    
    papers = fetch_pubmed_papers(args.query, args.debug)
    
    if args.file:
        save_to_csv(args.file, papers)
    else:
        print(papers)

if __name__ == "__main__":
    main()

