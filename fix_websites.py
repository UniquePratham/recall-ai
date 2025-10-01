#!/usr/bin/env python3
"""
Script to fix the AI coding websites in the database with proper information
"""
import asyncio
from utils import generate_embedding, store_in_vector_db

async def fix_ai_websites():
    """Add the AI coding websites with proper information"""
    username = "uniquepratham"
    
    # AI Coding websites with proper descriptions
    websites = [
        {
            "url": "https://app.emergent.sh/",
            "title": "Emergent - AI Coding Website and Project Builder",
            "description": "Emergent is an AI-powered coding platform and project builder that helps developers create applications using artificial intelligence assistance."
        },
        {
            "url": "https://v0.app/",
            "title": "v0 by Vercel - AI Coding Website and Project Builder", 
            "description": "v0 is Vercel's AI-powered interface design and coding platform that generates React components and full applications from text descriptions."
        },
        {
            "url": "https://mgx.dev/",
            "title": "MetaGPT X (MGX) - AI Coding Website and Project Builder",
            "description": "MetaGPT X (MGX) is an AI coding website and project builder platform for creating software projects with AI assistance."
        },
        {
            "url": "https://gamma.app/",
            "title": "Gamma - AI Presentations and Documents",
            "description": "Gamma is an AI-powered platform for creating presentations, documents, and web pages with intelligent design assistance."
        }
    ]
    
    print("Adding AI coding websites with proper information...")
    
    for i, website in enumerate(websites, 1):
        try:
            # Create comprehensive content for storage
            storage_text = f"""URL: {website['url']} - AI Coding Website and Project Builder
Title: {website['title']}
Description: {website['description']}
Category: AI Development Tools, Code Generation, Project Builder
Keywords: AI coding, project builder, development platform, code generation"""
            
            # Create embedding text that emphasizes the key terms
            embedding_text = f"AI Coding Website Project Builder: {website['title']} - {website['url']} - {website['description']}"
            
            print(f"{i}. Processing {website['url']}...")
            
            # Generate embedding
            embedding = await generate_embedding(embedding_text)
            
            # Store in vector database
            await store_in_vector_db(
                embedding,
                storage_text,
                username,
                metadata={
                    "url": website['url'],
                    "title": website['title'], 
                    "content_type": "ai_coding_website",
                    "category": "development_tools"
                }
            )
            
            print(f"   ✅ Successfully added {website['title']}")
            
        except Exception as e:
            print(f"   ❌ Error adding {website['url']}: {e}")
    
    print("\\n🎉 Finished adding AI coding websites!")
    print("\\nNow try searching for: 'List all my AI Coding Website Project Builder'")

if __name__ == "__main__":
    asyncio.run(fix_ai_websites())