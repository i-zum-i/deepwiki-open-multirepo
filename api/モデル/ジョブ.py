"""
ジョブデータモデル

DeepWiki-OMRの解析ジョブ管理に関するデータモデルを定義します。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import uuid


class ジョブ種別(str, Enum):
    """ジョブの種別"""
    PARSE_FULL = "PARSE_FULL"           # 全体解析
    PARSE_INCREMENTAL = "PARSE_INCREMENTAL"  # 差分解析
    WEBHOOK_PROCESS = "WEBHOOK_PROCESS"  # Webhook処理
    CLEANUP = "CLEANUP"                 # クリーンアップ


class ジョブステータス(str, Enum):
    """ジョブの状態"""
    PENDING = "PENDING"       # 待機中
    RUNNING = "RUNNING"       # 実行中
    COMPLETED = "COMPLETED"   # 完了
    FAILED = "FAILED"         # 失敗
    CANCELLED = "CANCELLED"   # キャンセル


class ジョブ優先度(str, Enum):
    """ジョブの優先度"""
    HIGH = "HIGH"       # 高優先度
    NORMAL = "NORMAL"   # 通常優先度
    LOW = "LOW"         # 低優先度


class ジョブ(BaseModel):
    """
    解析ジョブのメインデータモデル
    
    DynamoDBのジョブテーブルに対応
    """
    ジョブID: str = Field(..., description="ジョブの一意識別子")
    リポジトリID: str = Field(..., description="対象リポジトリID")
    種別: ジョブ種別 = Field(..., description="ジョブ種別")
    ステータス: ジョブステータス = Field(default=ジョブステータス.PENDING, description="ジョブ状態")
    優先度: ジョブ優先度 = Field(default=ジョブ優先度.NORMAL, description="ジョブ優先度")
    開始日時: Optional[datetime] = Field(None, description="実行開始日時")
    完了日時: Optional[datetime] = Field(None, description="実行完了日時")
    作成日時: datetime = Field(default_factory=datetime.now, description="作成日時")
    更新日時: datetime = Field(default_factory=datetime.now, description="更新日時")
    TTL: Optional[int] = Field(None, description="DynamoDB TTL（エポック秒）")
    実行者: Optional[str] = Field(None, description="ジョブ実行者（ユーザーID等）")
    エラーメッセージ: Optional[str] = Field(None, description="エラーメッセージ")
    進捗率: int = Field(default=0, description="進捗率（0-100）")
    処理済みファイル数: int = Field(default=0, description="処理済みファイル数")
    総ファイル数: Optional[int] = Field(None, description="総ファイル数")
    入力パラメータ: Optional[Dict[str, Any]] = Field(default_factory=dict, description="入力パラメータ")
    出力結果: Optional[Dict[str, Any]] = Field(default_factory=dict, description="出力結果")
    メタデータ: Optional[Dict[str, Any]] = Field(default_factory=dict, description="追加メタデータ")

    @validator('進捗率')
    def 進捗率妥当性を検証(cls, v):
        """進捗率の妥当性を検証"""
        if v < 0 or v > 100:
            raise ValueError('進捗率は0から100の間で指定してください')
        return v

    @validator('TTL', pre=True, always=True)
    def TTL自動設定(cls, v, values):
        """TTLを自動設定（作成から30日後）"""
        if v is None:
            作成日時 = values.get('作成日時', datetime.now())
            TTL日時 = 作成日時 + timedelta(days=30)
            return int(TTL日時.timestamp())
        return v

    def DynamoDB項目に変換(self) -> Dict[str, Any]:
        """DynamoDB項目形式に変換"""
        項目 = {
            'job_id': self.ジョブID,
            'repo_id': self.リポジトリID,
            'type': self.種別.value,
            'status': self.ステータス.value,
            'priority': self.優先度.value,
            'created_at': self.作成日時.isoformat(),
            'updated_at': self.更新日時.isoformat(),
            'ttl': self.TTL,
            'progress': self.進捗率,
            'processed_files': self.処理済みファイル数,
            'input_params': self.入力パラメータ,
            'output_result': self.出力結果,
            'metadata': self.メタデータ
        }
        
        if self.開始日時:
            項目['started_at'] = self.開始日時.isoformat()
        if self.完了日時:
            項目['completed_at'] = self.完了日時.isoformat()
        if self.実行者:
            項目['executor'] = self.実行者
        if self.エラーメッセージ:
            項目['error_message'] = self.エラーメッセージ
        if self.総ファイル数:
            項目['total_files'] = self.総ファイル数
            
        return 項目

    @classmethod
    def DynamoDB項目から作成(cls, 項目: Dict[str, Any]) -> 'ジョブ':
        """DynamoDB項目からインスタンスを作成"""
        return cls(
            ジョブID=項目['job_id'],
            リポジトリID=項目['repo_id'],
            種別=ジョブ種別(項目['type']),
            ステータス=ジョブステータス(項目['status']),
            優先度=ジョブ優先度(項目.get('priority', 'NORMAL')),
            開始日時=datetime.fromisoformat(項目['started_at']) if 項目.get('started_at') else None,
            完了日時=datetime.fromisoformat(項目['completed_at']) if 項目.get('completed_at') else None,
            作成日時=datetime.fromisoformat(項目['created_at']),
            更新日時=datetime.fromisoformat(項目['updated_at']),
            TTL=項目.get('ttl'),
            実行者=項目.get('executor'),
            エラーメッセージ=項目.get('error_message'),
            進捗率=項目.get('progress', 0),
            処理済みファイル数=項目.get('processed_files', 0),
            総ファイル数=項目.get('total_files'),
            入力パラメータ=項目.get('input_params', {}),
            出力結果=項目.get('output_result', {}),
            メタデータ=項目.get('metadata', {})
        )

    def 実行時間を計算(self) -> Optional[timedelta]:
        """ジョブの実行時間を計算"""
        if self.開始日時 and self.完了日時:
            return self.完了日時 - self.開始日時
        elif self.開始日時:
            return datetime.now() - self.開始日時
        return None

    def 完了したか(self) -> bool:
        """ジョブが完了したかを判定"""
        return self.ステータス in [ジョブステータス.COMPLETED, ジョブステータス.FAILED, ジョブステータス.CANCELLED]

    def 成功したか(self) -> bool:
        """ジョブが成功したかを判定"""
        return self.ステータス == ジョブステータス.COMPLETED


class ジョブ作成リクエスト(BaseModel):
    """ジョブ作成APIのリクエストモデル"""
    種別: ジョブ種別 = Field(..., description="ジョブ種別")
    優先度: ジョブ優先度 = Field(default=ジョブ優先度.NORMAL, description="ジョブ優先度")
    入力パラメータ: Optional[Dict[str, Any]] = Field(default_factory=dict, description="入力パラメータ")


class ジョブ作成レスポンス(BaseModel):
    """ジョブ作成APIのレスポンスモデル"""
    成功: bool = Field(..., description="作成成功フラグ")
    ジョブID: Optional[str] = Field(None, description="生成されたジョブID")
    メッセージ: str = Field(..., description="結果メッセージ")


class ジョブ詳細(BaseModel):
    """ジョブ詳細情報のレスポンスモデル"""
    ジョブID: str = Field(..., description="ジョブID")
    リポジトリID: str = Field(..., description="リポジトリID")
    種別: ジョブ種別 = Field(..., description="種別")
    ステータス: ジョブステータス = Field(..., description="ステータス")
    優先度: ジョブ優先度 = Field(..., description="優先度")
    開始日時: Optional[datetime] = Field(None, description="開始日時")
    完了日時: Optional[datetime] = Field(None, description="完了日時")
    作成日時: datetime = Field(..., description="作成日時")
    更新日時: datetime = Field(..., description="更新日時")
    実行者: Optional[str] = Field(None, description="実行者")
    エラーメッセージ: Optional[str] = Field(None, description="エラーメッセージ")
    進捗率: int = Field(..., description="進捗率")
    処理済みファイル数: int = Field(..., description="処理済みファイル数")
    総ファイル数: Optional[int] = Field(None, description="総ファイル数")
    実行時間: Optional[str] = Field(None, description="実行時間（文字列形式）")


class ジョブ一覧項目(BaseModel):
    """ジョブ一覧表示用のモデル"""
    ジョブID: str = Field(..., description="ジョブID")
    種別: ジョブ種別 = Field(..., description="種別")
    ステータス: ジョブステータス = Field(..., description="ステータス")
    優先度: ジョブ優先度 = Field(..., description="優先度")
    進捗率: int = Field(..., description="進捗率")
    作成日時: datetime = Field(..., description="作成日時")
    更新日時: datetime = Field(..., description="更新日時")


class ジョブ一覧レスポンス(BaseModel):
    """ジョブ一覧APIのレスポンスモデル"""
    ジョブ一覧: List[ジョブ一覧項目] = Field(..., description="ジョブ一覧")
    総件数: int = Field(..., description="総件数")


class ジョブ更新リクエスト(BaseModel):
    """ジョブ更新APIのリクエストモデル"""
    ステータス: Optional[ジョブステータス] = Field(None, description="ステータス")
    進捗率: Optional[int] = Field(None, description="進捗率")
    エラーメッセージ: Optional[str] = Field(None, description="エラーメッセージ")
    処理済みファイル数: Optional[int] = Field(None, description="処理済みファイル数")
    総ファイル数: Optional[int] = Field(None, description="総ファイル数")
    出力結果: Optional[Dict[str, Any]] = Field(None, description="出力結果")

    @validator('進捗率')
    def 進捗率妥当性を検証(cls, v):
        """進捗率の妥当性を検証"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('進捗率は0から100の間で指定してください')
        return v


class ジョブ統計(BaseModel):
    """ジョブ統計情報のレスポンスモデル"""
    総ジョブ数: int = Field(..., description="総ジョブ数")
    実行中ジョブ数: int = Field(..., description="実行中ジョブ数")
    待機中ジョブ数: int = Field(..., description="待機中ジョブ数")
    完了ジョブ数: int = Field(..., description="完了ジョブ数")
    失敗ジョブ数: int = Field(..., description="失敗ジョブ数")
    平均実行時間: Optional[str] = Field(None, description="平均実行時間")
    成功率: float = Field(..., description="成功率（%）")


def ジョブIDを生成() -> str:
    """新しいジョブIDを生成"""
    return f"job-{uuid.uuid4().hex[:12]}"


def SQSメッセージを作成(ジョブ: ジョブ) -> Dict[str, Any]:
    """ジョブからSQSメッセージを作成"""
    return {
        "job_id": ジョブ.ジョブID,
        "repo_id": ジョブ.リポジトリID,
        "type": ジョブ.種別.value,
        "priority": ジョブ.優先度.value,
        "input_params": ジョブ.入力パラメータ,
        "created_at": ジョブ.作成日時.isoformat()
    }


def SQSメッセージからジョブを復元(メッセージ: Dict[str, Any]) -> Dict[str, Any]:
    """SQSメッセージからジョブ情報を復元"""
    return {
        "ジョブID": メッセージ["job_id"],
        "リポジトリID": メッセージ["repo_id"],
        "種別": ジョブ種別(メッセージ["type"]),
        "優先度": ジョブ優先度(メッセージ["priority"]),
        "入力パラメータ": メッセージ.get("input_params", {}),
        "作成日時": datetime.fromisoformat(メッセージ["created_at"])
    }