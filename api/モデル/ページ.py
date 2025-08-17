"""
ページデータモデル

DeepWiki-OMRのWikiページ管理に関するデータモデルを定義します。
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import uuid


class ページ種別(str, Enum):
    """ページの種別"""
    README = "README"         # READMEページ
    CODE = "CODE"             # コードファイルページ
    DIRECTORY = "DIRECTORY"   # ディレクトリページ
    API = "API"               # API仕様ページ
    GUIDE = "GUIDE"           # ガイドページ


class ページステータス(str, Enum):
    """ページの状態"""
    ACTIVE = "ACTIVE"         # アクティブ
    DRAFT = "DRAFT"           # 下書き
    ARCHIVED = "ARCHIVED"     # アーカイブ済み


class ページ(BaseModel):
    """
    Wikiページのメインデータモデル
    
    DynamoDBのページテーブルに対応
    """
    リポジトリID: str = Field(..., description="所属するリポジトリID")
    ページID: str = Field(..., description="ページの一意識別子")
    タイトル: str = Field(..., description="ページタイトル")
    種別: ページ種別 = Field(..., description="ページ種別")
    ステータス: ページステータス = Field(default=ページステータス.ACTIVE, description="ページ状態")
    ソースパス: str = Field(..., description="元ソースファイルのパス")
    コンテンツ: str = Field(..., description="Wikiコンテンツ（Markdown）")
    要約: Optional[str] = Field(None, description="ページの要約")
    重要度: str = Field(default="medium", description="ページの重要度（high/medium/low）")
    関連ページ: List[str] = Field(default_factory=list, description="関連ページのIDリスト")
    タグ: List[str] = Field(default_factory=list, description="ページのタグ")
    S3キー: Optional[str] = Field(None, description="S3に保存されたコンテンツのキー")
    作成日時: datetime = Field(default_factory=datetime.now, description="作成日時")
    更新日時: datetime = Field(default_factory=datetime.now, description="更新日時")
    最終解析日時: Optional[datetime] = Field(None, description="最終解析日時")
    メタデータ: Optional[Dict[str, Any]] = Field(default_factory=dict, description="追加メタデータ")

    @validator('タイトル')
    def タイトル妥当性を検証(cls, v):
        """タイトルの妥当性を検証"""
        if not v or len(v.strip()) == 0:
            raise ValueError('タイトルは必須です')
        if len(v) > 200:
            raise ValueError('タイトルは200文字以内で入力してください')
        return v.strip()

    @validator('重要度')
    def 重要度妥当性を検証(cls, v):
        """重要度の妥当性を検証"""
        有効な重要度 = ['high', 'medium', 'low']
        if v not in 有効な重要度:
            raise ValueError(f'重要度は {", ".join(有効な重要度)} のいずれかを指定してください')
        return v

    def DynamoDB項目に変換(self) -> Dict[str, Any]:
        """DynamoDB項目形式に変換"""
        項目 = {
            'repo_id': self.リポジトリID,
            'page_id': self.ページID,
            'title': self.タイトル,
            'type': self.種別.value,
            'status': self.ステータス.value,
            'source_path': self.ソースパス,
            'content': self.コンテンツ,
            'importance': self.重要度,
            'related_pages': self.関連ページ,
            'tags': self.タグ,
            'created_at': self.作成日時.isoformat(),
            'updated_at': self.更新日時.isoformat(),
            'metadata': self.メタデータ
        }
        
        if self.要約:
            項目['summary'] = self.要約
        if self.S3キー:
            項目['s3_key'] = self.S3キー
        if self.最終解析日時:
            項目['last_parsed_at'] = self.最終解析日時.isoformat()
            
        return 項目

    @classmethod
    def DynamoDB項目から作成(cls, 項目: Dict[str, Any]) -> 'ページ':
        """DynamoDB項目からインスタンスを作成"""
        return cls(
            リポジトリID=項目['repo_id'],
            ページID=項目['page_id'],
            タイトル=項目['title'],
            種別=ページ種別(項目['type']),
            ステータス=ページステータス(項目.get('status', 'ACTIVE')),
            ソースパス=項目['source_path'],
            コンテンツ=項目['content'],
            要約=項目.get('summary'),
            重要度=項目.get('importance', 'medium'),
            関連ページ=項目.get('related_pages', []),
            タグ=項目.get('tags', []),
            S3キー=項目.get('s3_key'),
            作成日時=datetime.fromisoformat(項目['created_at']),
            更新日時=datetime.fromisoformat(項目['updated_at']),
            最終解析日時=datetime.fromisoformat(項目['last_parsed_at']) if 項目.get('last_parsed_at') else None,
            メタデータ=項目.get('metadata', {})
        )


class ページ作成リクエスト(BaseModel):
    """ページ作成APIのリクエストモデル"""
    タイトル: str = Field(..., description="ページタイトル")
    種別: ページ種別 = Field(..., description="ページ種別")
    ソースパス: str = Field(..., description="元ソースファイルのパス")
    コンテンツ: str = Field(..., description="Wikiコンテンツ")
    要約: Optional[str] = Field(None, description="ページの要約")
    重要度: str = Field(default="medium", description="ページの重要度")
    タグ: List[str] = Field(default_factory=list, description="ページのタグ")


class ページ更新リクエスト(BaseModel):
    """ページ更新APIのリクエストモデル"""
    タイトル: Optional[str] = Field(None, description="ページタイトル")
    コンテンツ: Optional[str] = Field(None, description="Wikiコンテンツ")
    要約: Optional[str] = Field(None, description="ページの要約")
    重要度: Optional[str] = Field(None, description="ページの重要度")
    ステータス: Optional[ページステータス] = Field(None, description="ページ状態")
    タグ: Optional[List[str]] = Field(None, description="ページのタグ")


class ページ詳細(BaseModel):
    """ページ詳細情報のレスポンスモデル"""
    リポジトリID: str = Field(..., description="リポジトリID")
    ページID: str = Field(..., description="ページID")
    タイトル: str = Field(..., description="タイトル")
    種別: ページ種別 = Field(..., description="種別")
    ステータス: ページステータス = Field(..., description="ステータス")
    ソースパス: str = Field(..., description="ソースパス")
    コンテンツ: str = Field(..., description="コンテンツ")
    要約: Optional[str] = Field(None, description="要約")
    重要度: str = Field(..., description="重要度")
    関連ページ: List[str] = Field(..., description="関連ページ")
    タグ: List[str] = Field(..., description="タグ")
    作成日時: datetime = Field(..., description="作成日時")
    更新日時: datetime = Field(..., description="更新日時")
    最終解析日時: Optional[datetime] = Field(None, description="最終解析日時")


class ページ一覧項目(BaseModel):
    """ページ一覧表示用のモデル"""
    ページID: str = Field(..., description="ページID")
    タイトル: str = Field(..., description="タイトル")
    種別: ページ種別 = Field(..., description="種別")
    ステータス: ページステータス = Field(..., description="ステータス")
    重要度: str = Field(..., description="重要度")
    更新日時: datetime = Field(..., description="更新日時")


class ページ一覧レスポンス(BaseModel):
    """ページ一覧APIのレスポンスモデル"""
    ページ一覧: List[ページ一覧項目] = Field(..., description="ページ一覧")
    総件数: int = Field(..., description="総件数")


class Wiki目次項目(BaseModel):
    """Wiki目次の項目モデル"""
    ページID: str = Field(..., description="ページID")
    タイトル: str = Field(..., description="タイトル")
    種別: ページ種別 = Field(..., description="種別")
    重要度: str = Field(..., description="重要度")
    子項目: List['Wiki目次項目'] = Field(default_factory=list, description="子項目")


class Wiki目次(BaseModel):
    """Wiki目次のレスポンスモデル"""
    リポジトリID: str = Field(..., description="リポジトリID")
    リポジトリ名: str = Field(..., description="リポジトリ名")
    ルート項目: List[Wiki目次項目] = Field(..., description="ルート項目")
    総ページ数: int = Field(..., description="総ページ数")
    最終更新日時: Optional[datetime] = Field(None, description="最終更新日時")


# 自己参照のためのモデル更新
Wiki目次項目.model_rebuild()


def ページIDを生成(リポジトリID: str, ソースパス: str) -> str:
    """ソースパスからページIDを生成"""
    # ソースパスをベースにしたハッシュ値を生成
    import hashlib
    パス_ハッシュ = hashlib.md5(ソースパス.encode()).hexdigest()[:8]
    return f"page-{リポジトリID}-{パス_ハッシュ}"


def ソースパスから種別を推定(ソースパス: str) -> ページ種別:
    """ソースパスからページ種別を推定"""
    パス_小文字 = ソースパス.lower()
    
    if 'readme' in パス_小文字:
        return ページ種別.README
    elif パス_小文字.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs')):
        return ページ種別.CODE
    elif 'api' in パス_小文字 or 'swagger' in パス_小文字 or 'openapi' in パス_小文字:
        return ページ種別.API
    elif 'doc' in パス_小文字 or 'guide' in パス_小文字 or 'tutorial' in パス_小文字:
        return ページ種別.GUIDE
    elif '/' in パス_小文字 and not パス_小文字.split('/')[-1]:
        return ページ種別.DIRECTORY
    else:
        return ページ種別.CODE


def 重要度を推定(ソースパス: str, コンテンツ: str) -> str:
    """ソースパスとコンテンツから重要度を推定"""
    パス_小文字 = ソースパス.lower()
    コンテンツ_小文字 = コンテンツ.lower()
    
    # 高重要度の判定
    高重要度_キーワード = ['readme', 'main', 'index', 'app', 'server', 'client', 'api']
    if any(キーワード in パス_小文字 for キーワード in 高重要度_キーワード):
        return 'high'
    
    # コンテンツの長さによる判定
    if len(コンテンツ) > 5000:
        return 'high'
    elif len(コンテンツ) > 1000:
        return 'medium'
    else:
        return 'low'