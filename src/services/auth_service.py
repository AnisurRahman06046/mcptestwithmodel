"""
Authentication service for token validation with platform API.
"""

import httpx
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException
from src.models.api import QueryContext

logger = logging.getLogger(__name__)


class AuthService:
    """Service for validating tokens and extracting user context."""
    
    def __init__(self):
        self.platform_api_url = "https://api.bitcommerz.com/api/v1/auth/validate-token"
        self.timeout = 10.0  # 10 seconds timeout
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate token with platform API and return user data.
        
        Args:
            token: Bearer token from request headers
            
        Returns:
            Dict containing user and shop information
            
        Raises:
            HTTPException: If token is invalid or API call fails
        """
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        try:
            logger.info("Validating token with platform API")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.platform_api_url, headers=headers)
                
                if response.status_code == 401:
                    logger.warning("Token validation failed - unauthorized")
                    raise HTTPException(status_code=401, detail="Invalid or expired token")
                
                if response.status_code != 200:
                    logger.error(f"Platform API error: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=503, 
                        detail="Authentication service temporarily unavailable"
                    )
                
                user_data = response.json()
                logger.info(f"Token validated successfully for user: {user_data.get('id')}")
                
                return user_data
                
        except httpx.TimeoutException:
            logger.error("Token validation timeout")
            raise HTTPException(
                status_code=503, 
                detail="Authentication service timeout"
            )
        except httpx.RequestError as e:
            logger.error(f"Token validation request error: {e}")
            raise HTTPException(
                status_code=503, 
                detail="Authentication service unavailable"
            )
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail="Internal authentication error"
            )
    
    def extract_query_context(self, user_data: Dict[str, Any]) -> QueryContext:
        """
        Extract QueryContext from validated user data.
        
        Args:
            user_data: Response from platform API
            
        Returns:
            QueryContext with user_id, shop_id, and other context
        """
        try:
            # Extract user and shop information
            user_id = str(user_data.get('id'))
            shop_id = str(user_data.get('shopId'))
            
            # Extract shop details if available
            shop = user_data.get('shop', {})
            currency = shop.get('currency', 'USD')
            country = shop.get('country', 'US')
            
            # Map country to timezone (simplified mapping)
            timezone_mapping = {
                'BD': 'Asia/Dhaka',
                'US': 'America/New_York', 
                'UK': 'Europe/London',
                'IN': 'Asia/Kolkata'
            }
            timezone = timezone_mapping.get(country, 'UTC')
            
            context = QueryContext(
                user_id=user_id,
                shop_id=shop_id,
                timezone=timezone,
                currency=currency
            )
            
            logger.info(f"Extracted context: user_id={user_id}, shop_id={shop_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error extracting query context: {e}", exc_info=True)
            # Fallback context
            return QueryContext(
                user_id=str(user_data.get('id', 'unknown')),
                shop_id=str(user_data.get('shopId', 'unknown')),
                timezone='UTC',
                currency='USD'
            )
    
    async def authenticate_request(self, token: str) -> QueryContext:
        """
        Complete authentication flow: validate token + extract context.
        
        Args:
            token: Bearer token from request headers
            
        Returns:
            QueryContext for the authenticated user/shop
        """
        user_data = await self.validate_token(token)
        context = self.extract_query_context(user_data)
        return context


# Global auth service instance
auth_service = AuthService()