# daily_digest_file.py - Secure version that saves to files
import asyncio
import logging
from datetime import datetime, timezone, timedelta
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
        """Search for papers across all research areas"""
        papers = []
        
        # Define research areas and queries
        research_areas = {
            "AI": [
                "artificial intelligence latest",
                "AI breakthrough",
                "deep learning advances"
            ],
            "Machine Learning": [
                "machine learning new methods",
                "ML algorithms novel",
                "learning systems"
            ],
            "LLM": [
                "large language models",
                "LLM applications",
                "transformer models"
            ],
            "Recommendation Systems": [
                "recommendation systems",
                "recommender systems",
                "personalization algorithms"
            ],
            "Multimodal": [
                "multimodal learning",
                "cross-modal",
                "vision language models"
            ],
            "IO Psychology": [
                "industrial organizational psychology",
                "workplace psychology",
                "organizational behavior"
            ],
            "HCI": [
                "human computer interaction",
                "user interface design",
                "usability research"
            ]
        }
        
        papers_by_area = {}
        
        for area, area_queries in research_areas.items():
            area_papers = []
            logger.info(f"Searching {area}...")
            
            for query in area_queries:
                try:
                    # Search with date filtering for recent papers
                    arxiv_papers = self.arxiv_searcher.search(query, max_results=3)
                    # Filter to today's papers (or yesterday if run early)
                    recent_arxiv = self.filter_recent_papers(arxiv_papers)
                    area_papers.extend(recent_arxiv)
                    
                    # Reduce API calls to avoid rate limits
                    if len(area_papers) < 5:  # Only search more if we need more papers
                        semantic_papers = self.semantic_searcher.search(query, max_results=2)
                        recent_semantic = self.filter_recent_papers(semantic_papers)
                        area_papers.extend(recent_semantic)
                    
                    if len(area_papers) < 3:  # Only search PubMed if still need papers
                        pubmed_papers = self.pubmed_searcher.search(query, max_results=2)
                        recent_pubmed = self.filter_recent_papers(pubmed_papers)
                        area_papers.extend(recent_pubmed)
                        
                except Exception as e:
                    logger.error(f"Error searching {area} - {query}: {e}")
            
            # Remove duplicates and limit per area
            area_papers = self.remove_duplicates(area_papers)[:5]  # Max 5 per area
            papers_by_area[area] = area_papers
            papers.extend(area_papers)
            
            logger.info(f"Found {len(area_papers)} papers in {area}")
        
        self.papers_by_area = papers_by_area  # Store for analysis
        return papers
    
    def filter_recent_papers(self, papers):
        """Filter papers to only include recent papers (within last 3 days)"""
        
        today = datetime.now().date()
        cutoff_date = today - timedelta(days=3)  # Last 3 days to capture more papers
        
        recent_papers = []
        for paper in papers:
            try:
                if hasattr(paper, 'published_date') and paper.published_date:
                    # Parse the published date
                    if isinstance(paper.published_date, str):
                        # Handle different date formats
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S+%f'):
                            try:
                                paper_date = datetime.strptime(paper.published_date.split('+')[0], fmt).date()
                                break
                            except:
                                continue
                        else:
                            # If we can't parse the date, include the paper (likely recent)
                            recent_papers.append(paper)
                            continue
                    else:
                        paper_date = paper.published_date.date()
                    
                    # Include if published within last 3 days
                    if paper_date >= cutoff_date:
                        recent_papers.append(paper)
                else:
                    # If no date available, include the paper (likely recent)
                    recent_papers.append(paper)
            except Exception as e:
                # If any error in date filtering, include the paper
                recent_papers.append(paper)
                
        return recent_papers
    
    def remove_duplicates(self, papers):
        """Remove duplicate papers based on title similarity"""
        unique_papers = []
        seen_titles = set()
        
        for paper in papers:
            # Create a normalized title for comparison
            normalized_title = ''.join(paper.title.lower().split())
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_papers.append(paper)
                
        return unique_papers
    
    def analyze_paper_impact(self, paper):
        """Analyze paper for key innovations and impact tags"""
        # Simple keyword-based analysis for now
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        
        # Define impact keywords
        innovation_keywords = {
            'breakthrough': ['breakthrough', 'novel', 'first', 'new approach', 'innovative'],
            'performance': ['sota', 'state-of-the-art', 'outperforms', 'best results', 'improved performance'],
            'efficiency': ['efficient', 'faster', 'optimized', 'reduced complexity', 'lightweight'],
            'method': ['method', 'algorithm', 'framework', 'approach', 'technique'],
            'application': ['application', 'real-world', 'practical', 'deployment', 'implementation'],
            'problem': ['problem', 'challenge', 'issue', 'limitation', 'bottleneck'],
            'solution': ['solution', 'solves', 'addresses', 'tackles', 'resolves'],
            'impact': ['significant', 'important', 'critical', 'major', 'substantial'],
            'scalability': ['scalable', 'large-scale', 'distributed', 'parallel'],
            'robustness': ['robust', 'reliable', 'stable', 'consistent']
        }
        
        tags = []
        text = f"{title_lower} {abstract_lower}"
        
        for category, keywords in innovation_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(category)
        
        # Add specific domain tags
        domain_tags = {
            'deep_learning': ['deep learning', 'neural network', 'cnn', 'rnn', 'transformer'],
            'llm': ['language model', 'llm', 'gpt', 'bert', 'transformer'],
            'multimodal': ['multimodal', 'vision', 'language', 'cross-modal'],
            'recommendation': ['recommendation', 'recommender', 'personalization'],
            'hci': ['human computer', 'user interface', 'usability', 'interaction'],
            'psychology': ['psychology', 'behavior', 'cognitive', 'organizational']
        }
        
        for domain, keywords in domain_tags.items():
            if any(keyword in text for keyword in keywords):
                tags.append(domain)
        
        return tags[:5]  # Limit to top 5 tags
    
    def assess_paper_impact(self, paper):
        """Assess the potential impact level of a paper"""
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        text = f"{title_lower} {abstract_lower}"
        
        # High impact indicators
        high_impact_keywords = [
            'breakthrough', 'novel', 'first', 'unprecedented', 'revolutionary',
            'sota', 'state-of-the-art', 'outperforms', 'significant improvement',
            'major advance', 'paradigm', 'fundamental'
        ]
        
        # Medium impact indicators
        medium_impact_keywords = [
            'improved', 'enhanced', 'better', 'efficient', 'effective',
            'robust', 'scalable', 'practical', 'real-world'
        ]
        
        high_score = sum(1 for keyword in high_impact_keywords if keyword in text)
        medium_score = sum(1 for keyword in medium_impact_keywords if keyword in text)
        
        if high_score >= 2:
            return "High"
        elif high_score >= 1 or medium_score >= 3:
            return "Medium"
        else:
            return "Standard"
    
    def analyze_trends(self):
        """Analyze trends across research areas"""
        if not hasattr(self, 'papers_by_area'):
            return {}
        
        trends = {}
        implementation_opportunities = []
        
        for area, papers in self.papers_by_area.items():
            if not papers:
                trends[area] = "No papers found today"
                continue
                
            # Analyze common themes
            all_text = " ".join([f"{paper.title} {paper.abstract}" for paper in papers if paper.abstract])
            common_terms = self.extract_common_terms(all_text, area)
            
            # Assess area trends
            area_trends = []
            if common_terms:
                area_trends.append(f"Focus on {', '.join(common_terms[:3])}")
            
            # Check for specific trend indicators
            trend_indicators = {
                'AI': ['multimodal', 'foundation models', 'efficiency', 'alignment'],
                'Machine Learning': ['federated learning', 'few-shot', 'self-supervised', 'robustness'],
                'LLM': ['fine-tuning', 'reasoning', 'alignment', 'efficiency'],
                'Recommendation Systems': ['personalization', 'fairness', 'explainability', 'real-time'],
                'Multimodal': ['vision-language', 'unified models', 'cross-modal'],
                'IO Psychology': ['remote work', 'ai in workplace', 'employee wellbeing'],
                'HCI': ['ai interfaces', 'accessibility', 'user experience']
            }
            
            if area in trend_indicators:
                for indicator in trend_indicators[area]:
                    if indicator in all_text.lower():
                        area_trends.append(f"Growing interest in {indicator}")
            
            trends[area] = "; ".join(area_trends) if area_trends else "Diverse research directions"
            
            # Generate implementation opportunities
            if papers:
                high_impact_papers = [p for p in papers if self.assess_paper_impact(p) == "High"]
                if high_impact_papers:
                    opportunity = f"{area}: {high_impact_papers[0].title} shows potential for industry application"
                    implementation_opportunities.append(opportunity)
        
        return {
            'trends': trends,
            'opportunities': implementation_opportunities[:5]  # Top 5 opportunities
        }
    
    def extract_common_terms(self, text, area):
        """Extract common technical terms from text"""
        # Simple term extraction - in production, you'd use NLP libraries
        text_lower = text.lower()
        
        # Domain-specific important terms
        domain_terms = {
            'AI': ['neural', 'deep learning', 'transformer', 'attention', 'generative'],
            'Machine Learning': ['supervised', 'unsupervised', 'reinforcement', 'optimization', 'classification'],
            'LLM': ['language model', 'fine-tuning', 'prompt', 'reasoning', 'alignment'],
            'Recommendation Systems': ['collaborative', 'content-based', 'matrix factorization', 'embedding'],
            'Multimodal': ['vision', 'language', 'audio', 'cross-modal', 'fusion'],
            'IO Psychology': ['workplace', 'organizational', 'behavior', 'performance', 'wellbeing'],
            'HCI': ['interface', 'interaction', 'usability', 'user experience', 'accessibility']
        }
        
        if area not in domain_terms:
            return []
            
        found_terms = []
        for term in domain_terms[area]:
            if term in text_lower:
                found_terms.append(term)
                
        return found_terms[:5]
    
    def generate_innovation_description(self, paper, tags):
        """Generate innovation description based on paper content and tags"""
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        
        # Look for key innovation indicators
        if 'novel' in title_lower or 'new' in title_lower:
            if 'algorithm' in title_lower or 'method' in title_lower:
                return "Novel algorithmic approach"
            elif 'framework' in title_lower:
                return "New framework development"
            elif 'model' in title_lower:
                return "Novel model architecture"
        
        if 'first' in abstract_lower:
            return "First-of-its-kind approach"
        
        # Based on tags
        if 'breakthrough' in tags:
            if 'multimodal' in tags:
                return "Breakthrough in multimodal learning"
            elif 'llm' in tags:
                return "Breakthrough in language modeling"
            else:
                return "Breakthrough methodology"
        
        if 'efficiency' in tags:
            return "Efficiency optimization technique"
        
        if 'method' in tags and 'robustness' in tags:
            return "Robust methodological framework"
        
        # Domain-specific innovations
        if 'recommendation' in tags:
            return "Advanced recommendation methodology"
        elif 'hci' in tags:
            return "Human-computer interaction innovation"
        elif 'psychology' in tags:
            return "Behavioral modeling approach"
        
        # Generic fallback
        return "Methodological advancement"
    
    def generate_achievement_description(self, paper, tags):
        """Generate achievement description based on paper content and tags"""
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        
        # Look for performance claims
        if 'outperform' in abstract_lower or 'outperforms' in abstract_lower:
            return "Outperforms existing methods"
        
        if 'sota' in abstract_lower or 'state-of-the-art' in abstract_lower:
            return "Achieves state-of-the-art performance"
        
        if 'significant' in abstract_lower and 'improvement' in abstract_lower:
            return "Significant performance improvement"
        
        if 'reduce' in abstract_lower or 'reduces' in abstract_lower:
            if 'cost' in abstract_lower:
                return "Reduces computational costs"
            elif 'time' in abstract_lower:
                return "Reduces processing time"
            else:
                return "Reduces system overhead"
        
        # Based on tags
        if 'performance' in tags:
            return "Enhanced performance metrics"
        
        if 'efficiency' in tags:
            return "Improved computational efficiency"
        
        if 'scalability' in tags:
            return "Enhanced scalability"
        
        if 'robustness' in tags:
            return "Improved robustness and stability"
        
        # Domain-specific achievements
        if 'multimodal' in tags:
            return "Unified cross-modal understanding"
        elif 'llm' in tags:
            return "Enhanced language understanding"
        elif 'recommendation' in tags:
            return "Better personalization accuracy"
        elif 'psychology' in tags:
            return "Improved behavioral prediction"
        elif 'hci' in tags:
            return "Enhanced user experience"
        
        # Generic fallback
        return "Demonstrates practical applicability"
    
    def format_digest(self, papers):
        """Format papers into comprehensive Markdown digest"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Convert to US Eastern time for display
        eastern = timezone(timedelta(hours=-5))  # EST (UTC-5)
        eastern_time = datetime.now(eastern).strftime('%B %d, %Y at %I:%M %p EST')
        
        # Calculate coverage and impact metrics
        coverage_areas = sum(1 for area, papers_list in self.papers_by_area.items() if papers_list)
        total_areas = len(self.papers_by_area)
        
        # Find highest impact paper
        highest_impact_paper = None
        highest_impact_level = "Standard"
        for paper in papers:
            impact = self.assess_paper_impact(paper)
            if impact == "High" and highest_impact_level != "High":
                highest_impact_paper = paper
                highest_impact_level = impact
            elif impact == "Medium" and highest_impact_level == "Standard":
                highest_impact_paper = paper
                highest_impact_level = impact
        
        # Get trend analysis
        trend_analysis = self.analyze_trends()
        
        markdown = f"""# 📚 Paper Digest - {datetime.now().strftime('%B %d, %Y')}
"""
        
        
        # Add papers by research area
        for area, area_papers in self.papers_by_area.items():
            if not area_papers:
                continue
                
            # Map areas to your preferred format
            area_mapping = {
                "AI": "🤖 AI & Machine Learning",
                "Machine Learning": "🤖 AI & Machine Learning", 
                "LLM": "🧠 Large Language Models",
                "Recommendation Systems": "📊 Recommendation Systems",
                "Multimodal": "🌐 Multimodal AI",
                "IO Psychology": "💼 I/O Psychology",
                "HCI": "🖥️ Human-Computer Interaction"
            }
            
            # Skip duplicates for combined AI & ML section
            if area == "Machine Learning":
                continue
                
            display_area = area_mapping.get(area, area)
            
            # Combine AI and ML papers
            if area == "AI":
                combined_papers = area_papers + self.papers_by_area.get("Machine Learning", [])
            else:
                combined_papers = area_papers
            
            markdown += f"{display_area} ✅\nLatest Papers Found:\n\n"
            
            for paper in combined_papers[:3]:  # Max 3 papers per area
                # Format date for display
                try:
                    if isinstance(paper.published_date, str):
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                            try:
                                date_obj = datetime.strptime(paper.published_date.split(' ')[0], fmt.split(' ')[0])
                                formatted_date = date_obj.strftime('%b %d, %Y')
                                break
                            except:
                                continue
                        else:
                            formatted_date = paper.published_date.split(' ')[0]
                    else:
                        formatted_date = paper.published_date.strftime('%b %d, %Y')
                except:
                    formatted_date = str(paper.published_date)
                
                # Extract ArXiv ID if available
                arxiv_id = ""
                if hasattr(paper, 'url') and 'arxiv.org' in paper.url:
                    try:
                        arxiv_id = paper.url.split('/')[-1]
                    except:
                        arxiv_id = ""
                
                # Get impact analysis
                tags = self.analyze_paper_impact(paper)
                innovation_desc = self.generate_innovation_description(paper, tags)
                achievement_desc = self.generate_achievement_description(paper, tags)
                
                markdown += f'''"{paper.title}" ({formatted_date})

Innovation: {innovation_desc}
Key Property: {achievement_desc}
Application: {paper.abstract[:100] + "..." if paper.abstract and len(paper.abstract) > 100 else "Application details in abstract"}'''
                
                if arxiv_id:
                    markdown += f"\nArXiv: {arxiv_id}"
                
                markdown += "\n\n\n"
        
        # Add trend analysis
        if trend_analysis and 'trends' in trend_analysis:
            markdown += "## 🔍 **Key Trends Observed Today**\n\n"
            
            for area, trend in trend_analysis['trends'].items():
                area_icon = {"AI": "🤖", "Machine Learning": "🔍", "LLM": "💬", 
                            "Recommendation Systems": "🎯", "Multimodal": "🎭", 
                            "IO Psychology": "🧠", "HCI": "👤"}.get(area, "📊")
                markdown += f"- **{area_icon} {area}:** {trend}\n"
            
            markdown += "\n"
        
        # Add implementation opportunities
        if trend_analysis and 'opportunities' in trend_analysis and trend_analysis['opportunities']:
            markdown += "## 💡 **High Impact Implementation Opportunities**\n\n"
            
            for i, opportunity in enumerate(trend_analysis['opportunities'], 1):
                markdown += f"{i}. {opportunity}\n"
            
            markdown += "\n"
        
        # Add summary section
        markdown += f"""## 📋 **Today's Summary**

- **Coverage:** {coverage_areas}/{total_areas} research areas had new papers
- **Total Papers:** {len(papers)} papers analyzed
- **Highest Impact:** {highest_impact_level} impact research identified"""

        if highest_impact_paper:
            markdown += f"""
- **Top Paper:** "{highest_impact_paper.title}" """
            
        markdown += f"""

---

## 🔧 **Customize Your Digest**

📧 **Research Areas:** AI • ML • LLM • RecSys • Multimodal • IO Psychology • HCI  
⏰ **Schedule:** Daily at 9 AM Eastern  
🎯 **Focus:** Latest trends and high-impact research  

*Generated automatically by your comprehensive research digest system*
"""
        
        return markdown
    
    def save_digest(self, markdown_content):
        """Save digest to mounted volume"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"ai_io_psychology_digest_{date_str}.md"
        
        # Save to output directory in project
        output_dir = "output"
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
    
    def convert_markdown_to_html(self, markdown_content):
        """Convert markdown to properly formatted HTML for email"""
        html_content = markdown_content
        
        # Handle headers
        html_content = html_content.replace('# ', '<h1 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">')
        html_content = html_content.replace('## ', '<h2 style="color: #34495e; margin-top: 30px; margin-bottom: 15px;">')
        
        # Handle bold text properly
        import re
        html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
        
        # Handle URLs with better formatting
        url_pattern = r'\[(.*?)\]\((.*?)\)'
        html_content = re.sub(url_pattern, r'<a href="\2" style="color: #3498db; text-decoration: none;">\1</a>', html_content)
        
        # Handle line breaks and paragraphs
        html_content = html_content.replace('\n\n', '</p><p style="margin: 15px 0; line-height: 1.6;">')
        html_content = html_content.replace('\n', '<br>')
        
        # Handle horizontal rules
        html_content = html_content.replace('---', '<hr style="border: none; border-top: 1px solid #bdc3c7; margin: 25px 0;">')
        
        # Wrap in proper HTML structure
        final_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Daily AI & IO Psychology Papers</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #2c3e50; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
    <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px;">
            <h1 style="margin: 0; font-size: 28px;">🧠 AI & IO Psychology Papers</h1>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Daily Research Digest</p>
        </div>
        
        <p style="margin: 15px 0; line-height: 1.6;">{html_content}</p>
        
        <div style="margin-top: 40px; padding: 20px; background: #ecf0f1; border-radius: 8px; text-align: center;">
            <p style="margin: 0; color: #7f8c8d; font-size: 14px;">
                📧 Generated automatically by your daily digest system<br>
                🕘 Delivered daily at 9 AM Eastern
            </p>
        </div>
    </div>
</body>
</html>
"""
        return final_html

    def send_digest_email(self, markdown_content):
        """Send digest via email"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        recipient = os.getenv('RECIPIENT_EMAIL')
        
        if not all([email_user, email_pass, recipient]):
            logger.error("Email configuration missing")
            return False
            
        try:
            # Convert markdown to well-formatted HTML
            html_content = self.convert_markdown_to_html(markdown_content)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🧠 Multi-Domain Research Digest - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = email_user
            msg['To'] = recipient
            
            # Add both plain text and HTML versions
            text_part = MIMEText(markdown_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
            server.quit()
            
            logger.info("Digest email sent successfully")
            print(f"📧 Email sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            print(f"❌ Email failed: {e}")
            return False
    
    def run(self):
        """Main execution function"""
        logger.info("Starting daily digest generation")
        papers = self.search_papers()
        logger.info(f"Found {len(papers)} papers")
        
        if papers:
            markdown_digest = self.format_digest(papers)
            
            # Save to file
            saved_file = self.save_digest(markdown_digest)
            if saved_file:
                print(f"📄 Daily digest saved: {saved_file}")
            
            # Send via email
            email_sent = self.send_digest_email(markdown_digest)
            if email_sent:
                print(f"✅ Daily digest emailed successfully!")
            else:
                print(f"❌ Failed to send email, but file saved locally")
        else:
            logger.warning("No papers found")

if __name__ == "__main__":
    digest = DailyDigest()
    digest.run()