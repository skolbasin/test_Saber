"""Tests for Redis client implementation."""

import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from app.infrastructure.cache.redis_client import RedisClient


@pytest.fixture
def redis_client():
    """Create Redis client for testing."""
    return RedisClient("redis://localhost:6379/15")


@pytest.fixture
def mock_redis():
    """Create mock Redis connection."""
    return AsyncMock()


class TestRedisClient:
    """Test cases for RedisClient."""

    @pytest.mark.asyncio
    async def test_connect_success(self, redis_client):
        """Test successful Redis connection."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis
            
            await redis_client.connect()
            
            assert redis_client._redis == mock_redis
            mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, redis_client, mock_redis):
        """Test Redis disconnection."""
        redis_client._redis = mock_redis
        
        await redis_client.disconnect()
        
        mock_redis.close.assert_called_once()
        assert redis_client._redis is None

    @pytest.mark.asyncio
    async def test_get_success(self, redis_client, mock_redis):
        """Test successful get operation."""
        mock_redis.get.return_value = '{"key": "value"}'
        redis_client._redis = mock_redis
        
        result = await redis_client.get("test_key")
        
        assert result == {"key": "value"}
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_not_found(self, redis_client, mock_redis):
        """Test get operation with non-existent key."""
        mock_redis.get.return_value = None
        redis_client._redis = mock_redis
        
        result = await redis_client.get("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_invalid_json(self, redis_client, mock_redis):
        """Test get operation with invalid JSON."""
        mock_redis.get.return_value = "invalid json"
        redis_client._redis = mock_redis
        
        result = await redis_client.get("test_key")
        
        assert result == "invalid json"

    @pytest.mark.asyncio
    async def test_set_success(self, redis_client, mock_redis):
        """Test successful set operation."""
        mock_redis.set.return_value = True
        redis_client._redis = mock_redis
        
        result = await redis_client.set("test_key", {"data": "value"})
        
        assert result is True
        mock_redis.set.assert_called_once_with("test_key", '{"data": "value"}')

    @pytest.mark.asyncio
    async def test_set_with_ttl_int(self, redis_client, mock_redis):
        """Test set operation with integer TTL."""
        mock_redis.setex.return_value = True
        redis_client._redis = mock_redis
        
        result = await redis_client.set("test_key", {"data": "value"}, ttl=300)
        
        assert result is True
        mock_redis.setex.assert_called_once_with("test_key", 300, '{"data": "value"}')

    @pytest.mark.asyncio
    async def test_set_with_ttl_timedelta(self, redis_client, mock_redis):
        """Test set operation with timedelta TTL."""
        mock_redis.setex.return_value = True
        redis_client._redis = mock_redis
        
        result = await redis_client.set("test_key", {"data": "value"}, ttl=timedelta(minutes=5))
        
        assert result is True
        mock_redis.setex.assert_called_once_with("test_key", 300, '{"data": "value"}')

    @pytest.mark.asyncio
    async def test_delete_success(self, redis_client, mock_redis):
        """Test successful delete operation."""
        mock_redis.delete.return_value = 1
        redis_client._redis = mock_redis
        
        result = await redis_client.delete("test_key")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_not_found(self, redis_client, mock_redis):
        """Test delete operation with non-existent key."""
        mock_redis.delete.return_value = 0
        redis_client._redis = mock_redis
        
        result = await redis_client.delete("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_client, mock_redis):
        """Test exists operation with existing key."""
        mock_redis.exists.return_value = 1
        redis_client._redis = mock_redis
        
        result = await redis_client.exists("test_key")
        
        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_client, mock_redis):
        """Test exists operation with non-existent key."""
        mock_redis.exists.return_value = 0
        redis_client._redis = mock_redis
        
        result = await redis_client.exists("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_expire_success(self, redis_client, mock_redis):
        """Test successful expire operation."""
        mock_redis.expire.return_value = True
        redis_client._redis = mock_redis
        
        result = await redis_client.expire("test_key", 300)
        
        assert result is True
        mock_redis.expire.assert_called_once_with("test_key", 300)

    @pytest.mark.asyncio
    async def test_expire_with_timedelta(self, redis_client, mock_redis):
        """Test expire operation with timedelta."""
        mock_redis.expire.return_value = True
        redis_client._redis = mock_redis
        
        result = await redis_client.expire("test_key", timedelta(minutes=5))
        
        assert result is True
        mock_redis.expire.assert_called_once_with("test_key", 300)

    @pytest.mark.asyncio
    async def test_increment(self, redis_client, mock_redis):
        """Test increment operation."""
        mock_redis.incrby.return_value = 5
        redis_client._redis = mock_redis
        
        result = await redis_client.increment("counter", 3)
        
        assert result == 5
        mock_redis.incrby.assert_called_once_with("counter", 3)

    @pytest.mark.asyncio
    async def test_get_ttl_success(self, redis_client, mock_redis):
        """Test get TTL operation."""
        mock_redis.ttl.return_value = 300
        redis_client._redis = mock_redis
        
        result = await redis_client.get_ttl("test_key")
        
        assert result == 300
        mock_redis.ttl.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_ttl_no_expiration(self, redis_client, mock_redis):
        """Test get TTL operation for key without expiration."""
        mock_redis.ttl.return_value = -1
        redis_client._redis = mock_redis
        
        result = await redis_client.get_ttl("test_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_pattern(self, redis_client, mock_redis):
        """Test clear pattern operation."""
        mock_redis.keys.return_value = ["key1", "key2", "key3"]
        mock_redis.delete.return_value = 3
        redis_client._redis = mock_redis
        
        result = await redis_client.clear_pattern("test:*")
        
        assert result == 3
        mock_redis.keys.assert_called_once_with("test:*")
        mock_redis.delete.assert_called_once_with("key1", "key2", "key3")

    @pytest.mark.asyncio
    async def test_clear_pattern_no_keys(self, redis_client, mock_redis):
        """Test clear pattern operation with no matching keys."""
        mock_redis.keys.return_value = []
        redis_client._redis = mock_redis
        
        result = await redis_client.clear_pattern("test:*")
        
        assert result == 0
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_ping_success(self, redis_client, mock_redis):
        """Test successful ping operation."""
        mock_redis.ping.return_value = True
        redis_client._redis = mock_redis
        
        result = await redis_client.ping()
        
        assert result is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_failure(self, redis_client, mock_redis):
        """Test ping operation failure."""
        mock_redis.ping.side_effect = Exception("Connection failed")
        redis_client._redis = mock_redis
        
        result = await redis_client.ping()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_info_success(self, redis_client, mock_redis):
        """Test successful get info operation."""
        info_data = {"redis_version": "6.2.0", "used_memory": "1024"}
        mock_redis.info.return_value = info_data
        redis_client._redis = mock_redis
        
        result = await redis_client.get_info()
        
        assert result == info_data
        mock_redis.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_info_failure(self, redis_client, mock_redis):
        """Test get info operation failure."""
        mock_redis.info.side_effect = Exception("Info failed")
        redis_client._redis = mock_redis
        
        result = await redis_client.get_info()
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_auto_connect_on_operations(self, redis_client):
        """Test automatic connection on operations."""
        with patch.object(redis_client, 'connect') as mock_connect:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            redis_client._redis = None
            
            with patch('redis.asyncio.from_url', return_value=mock_redis):
                await redis_client.get("test_key")
            
            mock_connect.assert_called_once()

    def test_get_redis_client_singleton(self):
        """Test Redis client singleton pattern."""
        from app.infrastructure.cache.redis_client import get_redis_client
        
        client1 = get_redis_client()
        client2 = get_redis_client()
        
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_redis_connection(self):
        """Test closing global Redis connection."""
        from app.infrastructure.cache import redis_client
        
        # Mock the global client
        mock_instance = AsyncMock()
        redis_client._redis_client = mock_instance
        
        await redis_client.close_redis_connection()
        
        mock_instance.disconnect.assert_called_once()
        assert redis_client._redis_client is None