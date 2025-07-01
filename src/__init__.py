"""
Aigen Science 프로젝트
AI 기반 뉴스 수집, 분석 및 추천 시스템
"""

# Core 모듈 (루트에 있는 celery_app.py)
from .celery_app import app, celery_app

# Services 모듈
from .services import (
    AdvancedRetrieval,
    PDFProcessor,
    WebSearchEngine,
    perform_web_search
)

__all__ = [
    # Core
    'app',
    'celery_app',
    
    # Services
    'AdvancedRetrieval',
    'PDFProcessor', 
    'WebSearchEngine',
    'perform_web_search'
]
