# daily_digest_file.py - Secure version that saves to files
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

class DailyDigest:
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
                arxiv_papers = self.arxiv_searcher.search(query, max_results=3)
                papers.extend(arxiv_papers)
                
                # Reduce Semantic Scholar calls to avoid rate limits
                semantic_papers = self.semantic_searcher.search(query, max_results=2)
                papers.extend(semantic_papers)
                
                # PubMed search
                pubmed_papers = self.pubmed_searcher.search(query, max_results=2)
                papers.extend(pubmed_papers)
                
            except Exception as e:
                logger.error(f"Error searching for {query}: {e}")
        
        return papers
    
    def format_digest(self, papers):
        """Format papers into Markdown digest"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Convert to US Eastern time for display
        from datetime import timezone, timedelta
        eastern = timezone(timedelta(hours=-5))  # EST (UTC-5)
        # Note: This doesn't account for DST, but gives approximate Eastern time
        eastern_time = datetime.now(eastern).strftime('%Y-%m-%d %I:%M %p EST')
        
        markdown = f"""# Daily AI & IO Psychology Papers Digest - {date_str}

**Total Papers Found:** {len(papers)}  
**Generated:** {eastern_time}

---

"""
        
        for i, paper in enumerate(papers[:15], 1):  # Limit to 15 papers
            # Extract DOI if available
            doi = getattr(paper, 'doi', None) or ""
            if hasattr(paper, 'url') and 'doi.org' in paper.url:
                # Extract DOI from URL if it's a DOI link
                if '/10.' in paper.url:
                    doi = paper.url.split('/10.')[1] if '/10.' in paper.url else ""
                    doi = f"10.{doi}" if doi else ""
            
            markdown += f"""## {i}. {paper.title}

**Authors:** {', '.join(paper.authors)}  
**Published:** {paper.published_date}  
**URL:** [{paper.url}]({paper.url})"""
            
            if doi:
                markdown += f"""  
**DOI:** [{doi}](https://doi.org/{doi})"""
            
            markdown += f"""

**Abstract:**  
{paper.abstract[:500]}{'...' if len(paper.abstract) > 500 else ''}

---

"""
        
        return markdown
    
    def save_digest(self, markdown_content):
        """Save digest to mounted volume"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"ai_io_psychology_digest_{date_str}.md"
        
        # Save to mounted volume that you can access from host
        output_dir = "/app/output"
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            logger.info(f"Digest saved to {filepath}")
            print(f"✅ Digest saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save digest: {e}")
            return None
    
    def run(self):
        """Main execution function"""
        logger.info("Starting daily digest generation")
        papers = self.search_papers()
        logger.info(f"Found {len(papers)} papers")
        
        if papers:
            markdown_digest = self.format_digest(papers)
            saved_file = self.save_digest(markdown_digest)
            if saved_file:
                print(f"📧 Daily digest ready: {saved_file}")
        else:
            logger.warning("No papers found")

if __name__ == "__main__":
    digest = DailyDigest()
    digest.run()