import redis
import json
import time
import traceback # 오류 추적을 위해 임포트

from src.config_loader.settings import SETTINGS

class Redis:
    def __init__(self):
        self.client = None
        self.host = SETTINGS.get("REDIS_HOST")
        self.port = SETTINGS.get("REDIS_PORT")
        self.db = SETTINGS.get("REDIS_DB")
        self.block_timeout = SETTINGS.get("REDIS_BLOCK_TIMEOUT", 30)

        self.incoming_articles_queue_name = SETTINGS.get("INCOMING_ARTICLES_QUEUE")
        if not self.incoming_articles_queue_name:
            print("CRITICAL WARNING (redis.py): INCOMING_ARTICLES_QUEUE가 config.yaml에 정의되지 않았거나 비어있습니다.")

        self.channels = {
            "raw": SETTINGS.get("REDIS_MQ_CHANNEL_RAW"),
            "pre_checked": SETTINGS.get("REDIS_MQ_CHANNEL_PRE_CHECKED"),
            "processed": SETTINGS.get("REDIS_MQ_CHANNEL_PROCESSED"),
            "filter1_passed": SETTINGS.get("REDIS_MQ_CHANNEL_FILTER1_PASSED"),
            "filter2_passed": SETTINGS.get("REDIS_MQ_CHANNEL_FILTER2_PASSED"),
            "embedding_processed": SETTINGS.get("REDIS_MQ_CHANNEL_EMBEDDING"),
            "filter3_passed": SETTINGS.get("REDIS_MQ_CHANNEL_FILTER3_PASSED"),
        }

    def connect_client(self):
        """Redis 서버에 연결합니다."""
        if self.client is None:
            try:
                self.client = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
                self.client.ping() # 연결 테스트
                print("✅ Redis: 클라이언트 연결 성공")
            except redis.exceptions.ConnectionError as e:
                print(f"❌ Redis: 클라이언트 연결 실패: {e}")
                self.client = None 
                raise
        return True

    def close_client(self):
        """Redis 클라이언트 연결을 닫습니다."""
        if self.client:
            self.client.close()
            self.client = None
            print("✅ Redis: 클라이언트 연결이 닫혔습니다.")

    def send_to_mq(self, channel_key: str, data: dict):
        """지정된 채널 키에 해당하는 Redis List에 데이터를 푸시합니다 (LPUSH)."""
        channel_name = self.channels.get(channel_key)
        if not channel_name:
            print(f"❌ Redis: 알 수 없는 MQ 채널 키: '{channel_key}'")
            return False
        if self.client is None:
            print("❌ Redis: 클라이언트가 연결되지 않아 MQ로 전송할 수 없습니다.")
            return False
        json_data = json.dumps(data, ensure_ascii=False)
        self.client.lpush(channel_name, json_data)
        return True

    def get_from_mq(self, channel_key: str):
        """지정된 채널 키에 해당하는 Redis List에서 메시지를 가져옵니다 (BRPOP)."""
        channel_name = self.channels.get(channel_key)
        if not channel_name:
            print(f"❌ Redis: 알 수 없는 MQ 채널 키: '{channel_key}'")
            return None
        if self.client is None:
            print("❌ Redis: 클라이언트가 연결되지 않아 메시지를 가져올 수 없습니다.")
            return None
        
        result = self.client.brpop(channel_name, timeout=self.block_timeout)
        if result:
            _queue_name_from_redis, json_data = result # 첫 번째 요소는 큐 이름이므로 _로 받음
            return json.loads(json_data)
        return None 
    
    # core_pipeline_manager.py에서 호출하려는 누락된 메서드
    def get_from_incoming_queue(self):
        """
        `self.incoming_articles_queue_name`에 지정된 Redis List에서 메시지를 가져옵니다 (BRPOP).
        """
        if not self.incoming_articles_queue_name:
            print("❌ Redis: 수신 큐 이름(incoming_articles_queue_name)이 설정되지 않았습니다.")
            return None
        if self.client is None:
            print("❌ Redis: 클라이언트가 연결되지 않아 수신 큐에서 메시지를 가져올 수 없습니다.")
            #
            return None

        result = self.client.brpop(self.incoming_articles_queue_name, timeout=self.block_timeout)
        if result:
            _queue_name_from_redis, json_data = result
            return json.loads(json_data)
        return None 
    def send_to_incoming_queue(self, data: dict):
        """
        `self.incoming_articles_queue_name`에 지정된 Redis List에 데이터를 푸시합니다 (LPUSH).
        """
        if not self.incoming_articles_queue_name:
            print("❌ Redis: 수신 큐 이름(incoming_articles_queue_name)이 설정되지 않았습니다. 데이터 전송 불가.")
            return False

        if self.client is None:
            print("❌ Redis: 클라이언트가 연결되지 않아 수신 큐로 전송할 수 없습니다.")
           
            return False 

        try:
            json_data = json.dumps(data, ensure_ascii=False)
            self.client.lpush(self.incoming_articles_queue_name, json_data)
            return True
        except redis.exceptions.RedisError as e_redis: 
            print(f"❌ Redis: Redis 작업 중 오류 발생 (큐: {self.incoming_articles_queue_name}): {e_redis}")
            traceback.print_exc()
            return False
        except TypeError as e_type: 
            print(f"❌ Redis: 데이터 직렬화 중 TypeError 발생 (큐: {self.incoming_articles_queue_name}): {e_type}")
            traceback.print_exc()
            return False
        except Exception as e: 
            print(f"❌ Redis: 수신 큐({self.incoming_articles_queue_name})로 데이터 전송 중 예기치 못한 오류 발생: {e}")
            traceback.print_exc()
            return False
# Redis 클래스의 인스턴스 생성 (다른 모듈에서 from src.config_loader.redis import r 로 임포트하여 사용)
r = Redis()