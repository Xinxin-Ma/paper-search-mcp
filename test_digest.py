# test_digest.py - Test version that saves to file
import asyncio
import logging
from datetime import datetime
import os
import sys
sys.path.append('/app')

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher
from paper_search_mcp.academic_platforms.semantic import SemanticSearcher
from paper_search_mcp.academic_platforms.pubmed import PubMedSearcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestDigest:
    def __init__(self):
        self.arxiv_searcher = ArxivSearcher()
        self.semantic_searcher = SemanticSearcher()
        self.pubmed_searcher = PubMedSearcher()
        
    def search_papers(self):
        """Search for AI + IO Psychology papers"""
        papers = []
        queries = [
            "AI industrial organizational psychology",
            "machine learning workplace behavior", 
            "artificial intelligence employee performance",
            "ML organizational behavior methodology"
        ]
        
        for query in queries:
            try:
                # ArXiv search
                arxiv_papers = self.arxiv_searcher.search(query, max_results=2)
                papers.extend(arxiv_papers)
                
                # Skip Semantic Scholar to avoid rate limits for testing
                # semantic_papers = self.semantic_searcher.search(query, max_results=2)
                # papers.extend(semantic_papers)
                
                # PubMed search
                pubmed_papers = self.pubmed_searcher.search(query, max_results=1)
                papers.extend(pubmed_papers)
                
            except Exception as e:
                logger.error(f"Error searching for {query}: {e}")
        
        return papers
    
    def format_digest(self, papers):
        """Format papers into HTML digest"""
        html = f"""
        <html>
        <body>
        <h2>Daily AI & IO Psychology Papers Digest - {datetime.now().strftime('%Y-%m-%d')}</h2>
        """
        
        for paper in papers[:10]:  # Limit to 10 papers
            html += f"""
            <div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #007acc;">
            <h3>{paper.title}</h3>
            <p><strong>Authors:</strong> {', '.join(paper.authors)}</p>
            <p><strong>Published:</strong> {paper.published_date}</p>
            <p><strong>Abstract:</strong> {paper.abstract[:300]}...</p>
            <p><a href="{paper.url}">Read Paper</a></p>
            </div>
            """
        
        html += "</body></html>"
        return html
    
    def save_digest(self, html_content):
        """Save digest to file"""
        filename = f"digest_{datetime.now().strftime('%Y-%m-%d')}.html"
        filepath = f"/tmp/{filename}"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Digest saved to {filepath}")
            print(f"Digest saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save digest: {e}")
    
    def run(self):
        """Main execution function"""
        logger.info("Starting test digest generation")
        papers = self.search_papers()
        logger.info(f"Found {len(papers)} papers")
        
        if papers:
            html_digest = self.format_digest(papers)
            self.save_digest(html_digest)
        else:
            logger.warning("No papers found")

if __name__ == "__main__":
    digest = TestDigest()
    digest.run()