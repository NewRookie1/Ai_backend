from datetime import datetime

class MarketProvider:
    async def get_analysis(self, category: str) -> dict:
        return {
            "category": category,
            "demand_score": 0.75,
            "average_price": 850,
            "total_listings": 1250,
            "trends": [
                {"period": "2024-01", "value": 0.65, "change_percent": 5.2},
                {"period": "2024-02", "value": 0.70, "change_percent": 7.7},
                {"period": "2024-03", "value": 0.75, "change_percent": 7.1},
            ],
            "summary": f"The {category} category shows growing demand. Handmade items in this category are trending with a 15% increase in searches over the last quarter.",
            "recommendation": "Consider expanding your product range in this category. Focus on unique designs and quality craftsmanship.",
            "confidence": 0.72,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    async def get_trends(self) -> list:
        return [
            {
                "category": "Home Decor",
                "demand_score": 0.85,
                "average_price": 1200,
                "total_listings": 3500,
                "trends": [
                    {"period": "2024-01", "value": 0.75, "change_percent": 8.5},
                    {"period": "2024-02", "value": 0.80, "change_percent": 6.7},
                    {"period": "2024-03", "value": 0.85, "change_percent": 6.3},
                ],
                "summary": "Home decor items are in high demand, especially handwoven and natural fiber products.",
                "recommendation": "Focus on sustainable, eco-friendly home decor items.",
                "confidence": 0.82,
                "analyzed_at": datetime.utcnow().isoformat(),
            },
            {
                "category": "Textiles",
                "demand_score": 0.78,
                "average_price": 2500,
                "total_listings": 2800,
                "trends": [
                    {"period": "2024-01", "value": 0.70, "change_percent": 5.0},
                    {"period": "2024-02", "value": 0.74, "change_percent": 5.7},
                    {"period": "2024-03", "value": 0.78, "change_percent": 5.4},
                ],
                "summary": "Handloom textiles continue to be popular. Natural dyes and traditional patterns are trending.",
                "recommendation": "Highlight the traditional craftsmanship and natural materials in your listings.",
                "confidence": 0.78,
                "analyzed_at": datetime.utcnow().isoformat(),
            },
            {
                "category": "Jewelry",
                "demand_score": 0.82,
                "average_price": 1800,
                "total_listings": 4200,
                "trends": [
                    {"period": "2024-01", "value": 0.78, "change_percent": 6.2},
                    {"period": "2024-02", "value": 0.80, "change_percent": 2.6},
                    {"period": "2024-03", "value": 0.82, "change_percent": 2.5},
                ],
                "summary": "Ethnic and traditional jewelry is seeing increased demand. Silver and brass items are popular.",
                "recommendation": "Create sets and offer customization options for better sales.",
                "confidence": 0.80,
                "analyzed_at": datetime.utcnow().isoformat(),
            },
        ]
    
    async def get_trending(self) -> list:
        return [
            {
                "name": "Handwoven Bamboo Basket",
                "category": "Home Decor",
                "trend_score": 0.92,
                "price_range": {"min": 500, "max": 1500},
            },
            {
                "name": "Block Print Cotton Saree",
                "category": "Textiles",
                "trend_score": 0.88,
                "price_range": {"min": 1500, "max": 4000},
            },
            {
                "name": "Terracotta Jewelry Set",
                "category": "Jewelry",
                "trend_score": 0.85,
                "price_range": {"min": 300, "max": 800},
            },
        ]
