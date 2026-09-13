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
        'SELF_NAME': ['your name', 'ur name', 'who are you', 'who r u'],
        'GREETING': ['hello', 'namaste', 'good morning', 'good afternoon'],
        'THANKS': ['thank you', 'thanks'],
        'BYE': ['goodbye', 'good bye', 'bye bye', 'see you'],
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
        
        voice_text, chat_text = await self._generate_response(
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
            "response": voice_text,
            "detailed_response": chat_text,
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
        
        voice_text, chat_text = await self._generate_response(
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
            "response": voice_text,
            "detailed_response": chat_text,
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
    
    @staticmethod
    def _inr(text: str) -> str:
        """Safety net: LLM sometimes prices in dollars. This app is India-only:
        turn $ amounts into ₹ amounts so chat/voice never say dollars."""
        import re
        text = re.sub(r"\$\s?(\d[\d,]*)", r"₹\1", text)
        text = re.sub(r"(?i)\bUS\s?dollars?\b", "rupees", text)
        text = re.sub(r"(?i)\b(\d[\d,]*)\s?dollars?\b", r"₹\1", text)
        return text

    @staticmethod
    def _extract_json(raw: str) -> dict:
        """Pull the first {...} JSON object out of model chatter."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("no JSON object")
        return json.loads(cleaned[start:end + 1])

    async def _generate_response(
        self,
        intent: str,
        text: str,
        user_language: str,
    ) -> tuple:
        """Returns (voice, chat): voice = one short spoken sentence,
        chat = properly formatted markdown shown in the chat bubble."""
        try:
            if user_language != "en":
                lang_map = {
                    'mr': 'Marathi', 'hi': 'Hindi', 'gu': 'Gujarati', 'bn': 'Bengali',
                    'ta': 'Tamil', 'te': 'Telugu', 'kn': 'Kannada', 'ml': 'Malayalam', 'pa': 'Punjabi',
                }
                lang_name = lang_map.get(user_language, user_language)
                # STRICT: reply ONLY in the user's selected language.
                lang_instruction = f" Write BOTH fields ONLY in {lang_name}. Never switch languages."
            else:
                # STRICT: user picked English — always reply in English,
                # even if they spoke with another accent or mixed words.
                lang_instruction = " Write BOTH fields ONLY in English. Never switch languages."

            response = chat_create(
                self.client,
                messages=[
                    {"role": "system", "content": (
                        "You are the warm, friendly voice assistant of the Artisan AI "
                        "artisan business app. The user's command was already "
                        "understood and the app is performing the action. "
                        f"{lang_instruction}".strip() +
                        " Reply with a single JSON object and nothing else, "
                        "with exactly these two keys: "
                        "'voice' = ONE short warm plain-text sentence (max 15 words) "
                        "confirming what is happening, no markdown; "
                        "'chat' = properly formatted markdown for the chat bubble: "
                        "a short bold heading plus 2-4 bullet points describing "
                        "what happened and the next step (max 120 words). "
                        "All prices in Indian Rupees with ₹ (never $ or dollars). "
                        "For UNKNOWN intent: echo the heard words, explain no "
                        "command matched so nothing was done, and list 3 example "
                        "commands. "
                        'Example: {"voice": "Opening your products.", '
                        '"chat": "**Your Products**\\n\\n- Browse your full catalog\\n- Tap a card for details"}'
                    )},
                    {"role": "user", "content": f"Intent: {intent}\nUser said: {text}"},
                ],
                models=text_models(),
                temperature=0.7,
                max_tokens=512,
            )

            raw = response.choices[0].message.content or ""
            try:
                data = self._extract_json(raw)
                voice = str(data.get("voice") or "").strip()
                chat = str(data.get("chat") or "").strip()
                if voice and chat:
                    return self._inr(voice), self._inr(chat)
            except Exception:
                pass
            # Model didn't return JSON: use raw as voice, wrap as chat.
            fallback_voice = raw.strip()[:200] or "Done."
            fallback_voice = self._inr(fallback_voice)
            return fallback_voice, fallback_voice
        except Exception:
            responses = {
                'NAVIGATE_HOME': ('Opening home screen.',
                                  '**Home**\n\n- You are on the home dashboard\n- Use quick actions below to continue'),
                'NAVIGATE_PRODUCTS': ('Opening your products.',
                                      '**Your Products**\n\n- Browse your full catalog\n- Tap any product for price and performance'),
                'NAVIGATE_ORDERS': ('Opening your orders.',
                                    '**Your Orders**\n\n- New, pending and past orders\n- Accept or update them from the list'),
                'NAVIGATE_MARKET': ('Opening market analysis.',
                                    '**Market Analysis**\n\n- Demand scores and trends\n- Check before you price a product'),
                'NAVIGATE_PROFILE': ('Opening your profile.',
                                     '**Profile**\n\n- Language, shop and payment settings\n- Switch seller/buyer mode here'),
                'NAVIGATE_SCANNER': ('Opening scanner. Point your camera at a product.',
                                     '**Scanner**\n\n- Point the camera at your product\n- Capture for instant AI analysis'),
                'SCAN_PRODUCT': ('Opening scanner to scan your product.',
                                 '**Scan Product**\n\n- Capture a clear photo\n- AI fills name, material and description'),
                'IDENTIFY_PRODUCT': ('Analyzing the product...',
                                     '**Analyzing…**\n\n- Reading material and craft type\n- Result appears in a moment'),
                'CREATE_PRODUCT': ('Let me help you create a new product. First, take a photo.',
                                   '**New Product**\n\n- Step 1: take a product photo\n- Step 2: review the AI-filled details\n- Step 3: save to your catalog'),
                'VIEW_PRODUCTS': ('Here are your products.',
                                  '**Your Products**\n\n- Full catalog below\n- Tap a card for details'),
                'VIEW_ORDERS': ('Here are your orders.',
                                '**Your Orders**\n\n- Latest orders first\n- Update status from each card'),
                'NEW_ORDERS': ('Checking for new orders...',
                               '**New Orders**\n\n- Pull down to refresh\n- Accept orders quickly to keep buyers happy'),
                'SUGGEST_PRICE': ('Let me suggest a price for this product.',
                                  '**Price Suggestion**\n\n- Enter material + labor cost\n- AI gives a range with reasoning'),
                'MARKET_ANALYSIS': ('Analyzing market data...',
                                    '**Market Analysis**\n\n- Demand and average prices\n- Recommendation for your category'),
                'MARKET_TRENDS': ('Here are the current market trends.',
                                  '**Market Trends**\n\n- What is selling now\n- Festive demand highlights'),
                'PRODUCT_PERFORMANCE': ('Showing your product performance.',
                                        '**Performance**\n\n- Views, orders and revenue\n- Focus on your top converter'),
                'HELP': ('I can help with scanning, catalog, orders, market and pricing.',
                         '**What I can do**\n\n- **Scan** products with the camera\n- **Manage** catalog and pricing\n- **Track** orders and market trends\n- Just speak or type a command'),
                'SELF_NAME': ("Meet Ai Sathi, the shop helper.",
                              '**Ai Sathi**\n\n- The voice helper for this shop app\n- Ask to show products, scan, or check orders'),
                'GREETING': ("Hello! What shall we do today?",
                             '**Hello!**\n\n- Try: *show my products*\n- Try: *scan product*\n- Try: *check new orders*'),
                'THANKS': ("Anytime! Happy to help with the shop.",
                           '**You are welcome**\n\n- Anything else for the shop today?'),
                'BYE': ("Bye! The shop helper stays right here.",
                        '**Bye!**\n\n- Come back any time for products, orders or pricing'),
                'UNKNOWN': (None, None),
            }
            if intent == 'UNKNOWN':
                heard = (text or '').strip() or '...'
                if len(heard) > 80:
                    heard = heard[:80] + '…'
                voice = (f'Hmm, {heard} — no matching command, '
                         'so nothing was done. Try show my products, '
                         'scan product, or check new orders.')
                chat = (f'**Hmm, that didn\'t come through**\n\n'
                        f'- Heard: “{heard}”\n'
                        '- Problem: no known command matches those words, so nothing was done\n'
                        '- Try: *show my products* · *scan product* · *check new orders*')
            else:
                voice, chat = responses.get(
                    intent, ('Hmm, that did not come through.',
                             '**Hmm**\n\n- Please rephrase your request'))
            # The reply must be in the user's language even when the LLM
            # is unreachable: translate the canned reply best-effort.
            if user_language and user_language != "en":
                try:
                    from .translation import TranslationProvider
                    translator = TranslationProvider()
                    t = await translator.translate(chat, user_language, "en")
                    chat = t.get("translated_text") or chat
                    t2 = await translator.translate(voice, user_language, "en")
                    voice = t2.get("translated_text") or voice
                except Exception:
                    pass
            return voice, chat
