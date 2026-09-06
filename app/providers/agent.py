from typing import Optional
from sqlalchemy.orm import Session
import openai
import json
from ..core.config import settings
from .model_fallback import chat_create, text_models

class AgentProvider:
    INTENT_PATTERNS = {
        'NAVIGATE_HOME': ['home', 'go home', 'main screen'],
        'NAVIGATE_PRODUCTS': ['products', 'catalog', 'my products', 'show products'],
        'NAVIGATE_ORDERS': ['orders', 'my orders', 'show orders'],
        'NAVIGATE_MARKET': ['market', 'market analysis', 'trends'],
        'NAVIGATE_PROFILE': ['profile', 'my profile', 'account'],
        'NAVIGATE_SCANNER': ['scanner', 'scan', 'camera', 'open scanner'],
        'SCAN_PRODUCT': ['scan this', 'scan product', 'scan it'],
        'IDENTIFY_PRODUCT': ['what is this', 'identify', 'what product is this'],
        'CREATE_PRODUCT': ['add product', 'create product', 'new product', 'add to catalog'],
        'VIEW_PRODUCTS': ['show products', 'my products', 'catalog'],
        'VIEW_ORDERS': ['show orders', 'my orders', 'orders'],
        'NEW_ORDERS': ['new orders', 'any new orders'],
        'SUGGEST_PRICE': ['price', 'how much', 'charge', 'pricing'],
        'MARKET_ANALYSIS': ['market analysis', 'market demand'],
        'MARKET_TRENDS': ['trends', 'what is trending'],
        'PRODUCT_PERFORMANCE': ['performance', 'how are my products doing', 'best selling'],
        'HELP': ['help', 'what can you do', 'commands'],
    }
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE,
        )
    
    async def process_voice(
        self,
        audio_content: bytes,
        filename: str,
        user_id: str,
        current_screen: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_language: Optional[str] = "en",
        image_path: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict:
        from .speech_to_text import SpeechToTextProvider
        stt = SpeechToTextProvider()
        
        stt_result = await stt.transcribe(audio_content, filename)
        transcript = stt_result["transcript"]
        detected_language = stt_result["language"]
        
        normalized_text = await self._normalize_text(transcript, detected_language)
        
        intent_result = self._detect_intent(normalized_text)
        
        response_text = await self._generate_response(
            intent=intent_result["intent"],
            text=normalized_text,
            user_language=user_language,
        )
        
        return {
            "conversation_id": conversation_id,
            "detected_language": detected_language,
            "transcript": transcript,
            "normalized_text": normalized_text,
            "intent": intent_result["intent"],
            "actions": intent_result["actions"],
            "entities": intent_result.get("entities", {}),
            "confidence": intent_result["confidence"],
            "requires_confirmation": intent_result.get("requires_confirmation", False),
            "response": response_text,
            "original_text": transcript,
        }
    
    async def process_text(
        self,
        text: str,
        user_id: str,
        current_screen: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_language: Optional[str] = "en",
        image_path: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict:
        normalized_text = await self._normalize_text(text, user_language)
        
        intent_result = self._detect_intent(normalized_text)
        
        response_text = await self._generate_response(
            intent=intent_result["intent"],
            text=normalized_text,
            user_language=user_language,
        )
        
        return {
            "conversation_id": conversation_id,
            "detected_language": user_language,
            "transcript": text,
            "normalized_text": normalized_text,
            "intent": intent_result["intent"],
            "actions": intent_result["actions"],
            "entities": intent_result.get("entities", {}),
            "confidence": intent_result["confidence"],
            "requires_confirmation": intent_result.get("requires_confirmation", False),
            "response": response_text,
            "original_text": text,
        }
    
    async def _normalize_text(self, text: str, source_language: str) -> str:
        if not source_language or source_language == "en":
            return text

        try:
            from .translation import TranslationProvider
            translator = TranslationProvider()
            result = await translator.translate(text, "en", source_language)
            return result.get("translated_text") or text
        except Exception:
            # Translation unavailable: match intents against the raw text.
            return text
    
    def _detect_intent(self, text: str) -> dict:
        normalized = text.lower().strip()
        
        best_intent = "UNKNOWN"
        best_score = 0
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                # Ignore tiny patterns to avoid false hits inside long text.
                if len(pattern) < 4:
                    continue
                if pattern in normalized:
                    score = len(pattern) / len(normalized)
                    if score > best_score:
                        best_score = score
                        best_intent = intent
        
        # Threshold kept low on purpose: natural sentences
        # ("show my products and check new orders") dilute the ratio.
        if best_score < 0.2:
            return {
                "intent": "UNKNOWN",
                "actions": [],
                "confidence": 0,
                "response": "I am not sure what you want. Can you tell me more?",
            }
        
        actions = self._build_actions(best_intent)
        confidence = min(best_score, 1.0)
        
        requires_confirmation = best_intent in [
            "DELETE_PRODUCT", "CANCEL_ORDER", "ACCEPT_ORDER", "REJECT_ORDER"
        ]
        
        return {
            "intent": best_intent,
            "actions": actions,
            "confidence": confidence,
            "requires_confirmation": requires_confirmation,
        }
    
    def _build_actions(self, intent: str) -> list:
        actions_map = {
            'NAVIGATE_HOME': [{"tool": "navigate", "parameters": {"target": "home"}}],
            'NAVIGATE_PRODUCTS': [{"tool": "navigate", "parameters": {"target": "products"}}],
            'NAVIGATE_ORDERS': [{"tool": "navigate", "parameters": {"target": "orders"}}],
            'NAVIGATE_MARKET': [{"tool": "navigate", "parameters": {"target": "market"}}],
            'NAVIGATE_PROFILE': [{"tool": "navigate", "parameters": {"target": "profile"}}],
            'NAVIGATE_SCANNER': [{"tool": "open_scanner", "parameters": {}}],
            'SCAN_PRODUCT': [
                {"tool": "open_scanner", "parameters": {}},
                {"tool": "capture_image", "parameters": {}},
                {"tool": "analyze_image", "parameters": {"purpose": "product_analysis"}},
            ],
            'CREATE_PRODUCT': [
                {"tool": "open_scanner", "parameters": {}},
                {"tool": "capture_image", "parameters": {}},
                {"tool": "analyze_image", "parameters": {"purpose": "product_creation"}},
                {"tool": "generate_product_listing", "parameters": {}},
                {"tool": "create_product", "parameters": {}},
            ],
            'VIEW_PRODUCTS': [{"tool": "navigate", "parameters": {"target": "products"}}],
            'VIEW_ORDERS': [{"tool": "navigate", "parameters": {"target": "orders"}}],
            'NEW_ORDERS': [{"tool": "get_new_orders", "parameters": {}}],
            'SUGGEST_PRICE': [{"tool": "suggest_price", "parameters": {}}],
            'MARKET_ANALYSIS': [{"tool": "get_market_analysis", "parameters": {}}],
            'MARKET_TRENDS': [{"tool": "get_market_trends", "parameters": {}}],
            'PRODUCT_PERFORMANCE': [{"tool": "get_product_performance", "parameters": {}}],
            'HELP': [{"tool": "show_help", "parameters": {}}],
        }
        
        return actions_map.get(intent, [])
    
    async def _generate_response(
        self,
        intent: str,
        text: str,
        user_language: str,
    ) -> str:
        try:
            lang_instruction = ""
            if user_language != "en":
                from .translation import TranslationProvider
                translator = TranslationProvider()
                lang_map = {
                    'mr': 'Marathi', 'hi': 'Hindi', 'gu': 'Gujarati', 'bn': 'Bengali',
                    'ta': 'Tamil', 'te': 'Telugu', 'kn': 'Kannada', 'ml': 'Malayalam', 'pa': 'Punjabi',
                }
                lang_name = lang_map.get(user_language, user_language)
                lang_instruction = f" Respond in {lang_name} language."
            
            response = chat_create(
                self.client,
                messages=[
                    {"role": "system", "content": (
                        "You are the built-in voice assistant of the Artisan AI "
                        "artisan business app. The user's command was already "
                        "understood and the app is performing the action. "
                        "Reply with ONE short plain-text sentence (max 15 words) "
                        "confirming what is happening. No markdown, no lists, "
                        "no formatting, no tutorials, no phone/computer how-tos. "
                        f"{lang_instruction}".strip()
                    )},
                    {"role": "user", "content": f"Intent: {intent}\nUser said: {text}"},
                ],
                models=text_models(),
                temperature=0.7,
                max_tokens=256,
            )
            
            return response.choices[0].message.content
        except Exception:
            responses = {
                'NAVIGATE_HOME': 'Opening home screen.',
                'NAVIGATE_PRODUCTS': 'Opening your products.',
                'NAVIGATE_ORDERS': 'Opening your orders.',
                'NAVIGATE_MARKET': 'Opening market analysis.',
                'NAVIGATE_PROFILE': 'Opening your profile.',
                'NAVIGATE_SCANNER': 'Opening scanner. Point your camera at a product.',
                'SCAN_PRODUCT': 'Opening scanner to scan your product.',
                'IDENTIFY_PRODUCT': 'Analyzing the product...',
                'CREATE_PRODUCT': 'Let me help you create a new product. First, take a photo.',
                'VIEW_PRODUCTS': 'Here are your products.',
                'VIEW_ORDERS': 'Here are your orders.',
                'NEW_ORDERS': 'Checking for new orders...',
                'SUGGEST_PRICE': 'Let me suggest a price for this product.',
                'MARKET_ANALYSIS': 'Analyzing market data...',
                'MARKET_TRENDS': 'Here are the current market trends.',
                'PRODUCT_PERFORMANCE': 'Showing your product performance.',
                'HELP': 'I can help you with: scanning products, managing your catalog, checking orders, market analysis, and pricing.',
                'UNKNOWN': 'I am not sure what you want. Can you tell me more?',
            }
            fallback = responses.get(intent, 'I am not sure what you want.')
            # The reply must be in the user's language even when the LLM
            # is unreachable: translate the canned reply best-effort.
            if user_language and user_language != "en":
                try:
                    from .translation import TranslationProvider
                    translator = TranslationProvider()
                    t = await translator.translate(fallback, user_language, "en")
                    return t.get("translated_text") or fallback
                except Exception:
                    pass
            return fallback
