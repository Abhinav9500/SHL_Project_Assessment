import csv
import json
import os
from vector_engine import collection

# The 9 queries from the Unlabeled Test Set (Appendix 1 & 2)
test_queries = [
    "I am hiring for Java developers who can also collaborate effectively with my business teams.",
    "Looking to hire mid-level professionals who are proficient in Python, SQL and Java Script.",
    "I am hiring for an analyst and wants applications to screen using Cognitive and personality tests",
    "Need a project manager with strong leadership skills and experience in agile methodology.",
    "Hiring for a customer service role that requires high empathy and problem-solving skills.",
    "Looking for a data scientist proficient in R, Python, and machine learning concepts.",
    "I need to hire a senior accountant who is detail-oriented and knows GAAP principles.",
    "Hiring for a sales representative role with a focus on negotiation and relationship building.",
    "Need a test for a software QA engineer experienced in manual and automated testing."
]

def generate_csv():
    output_file = "predictions.csv"
    
    print(f"Generating predictions for {len(test_queries)} queries...")
    
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # PDF Requirement: Header must be exactly Query and Assessment_url [cite: 212-213]
        writer.writerow(["Query", "Assessment_url"])
        
        for query in test_queries:
            # Get top 3 recommendations for each query as a safety margin
            results = collection.query(query_texts=[query], n_results=3)
            
            if results['metadatas'] and results['metadatas'][0]:
                for metadata in results['metadatas'][0]:
                    writer.writerow([query, metadata['url']])
            else:
                print(f"No results found for query: {query}")

    print(f"Successfully saved results to {output_file}")

if __name__ == "__main__":
    generate_csv()