"""
リポジトリデータモデル

DeepWiki-OMRのリポジトリ管理に関するデータモデルを定義します。
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import re
import uuid


class リポジトリプロバイダー(str, Enum):
    """リポジトリプロバイダーの種別"""
    GITHUB = "github"
    CODECOMMIT = "codecommit"


class リポジトリステータス(str, Enum):
    """リポジトリの処理状態"""
    READY = "READY"           # 準備完了
    PARSING = "PARSING"       # 解析中
    FAILED = "FAILED"         # 失敗


class 解析種別(str, Enum):
    """解析の種別"""
    FULL = "FULL"             # 全体解析
    INCREMENTAL = "INCREMENTAL"  # 差分解析


class リポジトリ(BaseModel):
    """
    リポジトリのメインデータモデル
    
    DynamoDBのリポジトリテーブルに対応
    """
    リポジトリID: str = Field(..., description="リポジトリの一意識別子")
    プロバイダー: リポジトリプロバイダー = Field(..., description="リポジトリプロバイダー")
    リモートURL: str = Field(..., description="リポジトリのURL")
    表示名: str = Field(..., description="表示用の名前")
    デフォルトブランチ: str = Field(default="main", description="デフォルトブランチ")
    ステータス: リポジトリステータス = Field(default=リポジトリステータス.READY, description="処理状態")
    最終スキャンSHA: Optional[str] = Field(None, description="最後にスキャンしたコミットSHA")
    最終スキャン日時: Optional[datetime] = Field(None, description="最終スキャン実行日時")
    作成日時: datetime = Field(default_factory=datetime.now, description="作成日時")
    更新日時: datetime = Field(default_factory=datetime.now, description="更新日時")
    削除フラグ: bool = Field(default=False, description="論理削除フラグ")
    メタデータ: Optional[Dict[str, Any]] = Field(default_factory=dict, description="追加メタデータ")

    @validator('リモートURL')
    def URL妥当性を検証(cls, v, values):
        """リモートURLの妥当性を検証"""
        プロバイダー = values.get('プロバイダー')
        
        if プロバイダー == リポジトリプロバイダー.GITHUB:
            # GitHub URL パターン
            github_patterns = [
                r'^https://github\.com/[^/]+/[^/]+\.git$',
                r'^https://github\.com/[^/]+/[^/]+$',
                r'^git@github\.com:[^/]+/[^/]+\.git$'
            ]
            if not any(re.match(pattern, v) for pattern in github_patterns):
                raise ValueError('無効なGitHub URL形式です')
                
        elif プロバイダー == リポジトリプロバイダー.CODECOMMIT:
            # CodeCommit URL パターン
            codecommit_patterns = [
                r'^codecommit://[^/]+$',
                r'^codecommit::[^:]+://[^/]+$',
                r'^https://git-codecommit\.[^.]+\.amazonaws\.com/v1/repos/[^/]+$'
            ]
            if not any(re.match(pattern, v) for pattern in codecommit_patterns):
                raise ValueError('無効なCodeCommit URL形式です')
        
        return v

    @validator('表示名')
    def 表示名妥当性を検証(cls, v):
        """表示名の妥当性を検証"""
        if not v or len(v.strip()) == 0:
            raise ValueError('表示名は必須です')
        if len(v) > 100:
            raise ValueError('表示名は100文字以内で入力してください')
        return v.strip()

    def DynamoDB項目に変換(self) -> Dict[str, Any]:
        """DynamoDB項目形式に変換"""
        項目 = {
            'repo_id': self.リポジトリID,
            'provider': self.プロバイダー.value,
            'remote_url': self.リモートURL,
            'display_name': self.表示名,
            'default_branch': self.デフォルトブランチ,
            'status': self.ステータス.value,
            'created_at': self.作成日時.isoformat(),
            'updated_at': self.更新日時.isoformat(),
            'deleted': self.削除フラグ,
            'metadata': self.メタデータ
        }
        
        if self.最終スキャンSHA:
            項目['last_scan_sha'] = self.最終スキャンSHA
        if self.最終スキャン日時:
            項目['last_scan_at'] = self.最終スキャン日時.isoformat()
            
        return 項目

    @classmethod
    def DynamoDB項目から作成(cls, 項目: Dict[str, Any]) -> 'リポジトリ':
        """DynamoDB項目からインスタンスを作成"""
        return cls(
            リポジトリID=項目['repo_id'],
            プロバイダー=リポジトリプロバイダー(項目['provider']),
            リモートURL=項目['remote_url'],
            表示名=項目['display_name'],
            デフォルトブランチ=項目.get('default_branch', 'main'),
            ステータス=リポジトリステータス(項目.get('status', 'READY')),
            最終スキャンSHA=項目.get('last_scan_sha'),
            最終スキャン日時=datetime.fromisoformat(項目['last_scan_at']) if 項目.get('last_scan_at') else None,
            作成日時=datetime.fromisoformat(項目['created_at']),
            更新日時=datetime.fromisoformat(項目['updated_at']),
            削除フラグ=項目.get('deleted', False),
            メタデータ=項目.get('metadata', {})
        )


class リポジトリ登録リクエスト(BaseModel):
    """リポジトリ登録APIのリクエストモデル"""
    プロバイダー: リポジトリプロバイダー = Field(..., description="リポジトリプロバイダー")
    リモートURL: str = Field(..., description="リポジトリのURL")
    表示名: str = Field(..., description="表示用の名前")
    デフォルトブランチ: Optional[str] = Field("main", description="デフォルトブランチ")

    @validator('リモートURL')
    def URL妥当性を検証(cls, v, values):
        """リモートURLの妥当性を検証"""
        プロバイダー = values.get('プロバイダー')
        
        if プロバイダー == リポジトリプロバイダー.GITHUB:
            github_patterns = [
                r'^https://github\.com/[^/]+/[^/]+\.git$',
                r'^https://github\.com/[^/]+/[^/]+$',
                r'^git@github\.com:[^/]+/[^/]+\.git$'
            ]
            if not any(re.match(pattern, v) for pattern in github_patterns):
                raise ValueError('無効なGitHub URL形式です')
                
        elif プロバイダー == リポジトリプロバイダー.CODECOMMIT:
            codecommit_patterns = [
                r'^codecommit://[^/]+$',
                r'^codecommit::[^:]+://[^/]+$',
                r'^https://git-codecommit\.[^.]+\.amazonaws\.com/v1/repos/[^/]+$'
            ]
            if not any(re.match(pattern, v) for pattern in codecommit_patterns):
                raise ValueError('無効なCodeCommit URL形式です')
        
        return v


class リポジトリ登録レスポンス(BaseModel):
    """リポジトリ登録APIのレスポンスモデル"""
    成功: bool = Field(..., description="登録成功フラグ")
    リポジトリID: Optional[str] = Field(None, description="生成されたリポジトリID")
    メッセージ: str = Field(..., description="結果メッセージ")


class リポジトリ詳細(BaseModel):
    """リポジトリ詳細情報のレスポンスモデル"""
    リポジトリID: str = Field(..., description="リポジトリID")
    プロバイダー: リポジトリプロバイダー = Field(..., description="プロバイダー")
    リモートURL: str = Field(..., description="リモートURL")
    表示名: str = Field(..., description="表示名")
    デフォルトブランチ: str = Field(..., description="デフォルトブランチ")
    ステータス: リポジトリステータス = Field(..., description="ステータス")
    最終スキャンSHA: Optional[str] = Field(None, description="最終スキャンSHA")
    最終スキャン日時: Optional[datetime] = Field(None, description="最終スキャン日時")
    作成日時: datetime = Field(..., description="作成日時")
    更新日時: datetime = Field(..., description="更新日時")
    ページ数: Optional[int] = Field(None, description="生成されたページ数")
    最新ジョブ: Optional[Dict[str, Any]] = Field(None, description="最新のジョブ情報")


class リポジトリ一覧項目(BaseModel):
    """リポジトリ一覧表示用のモデル"""
    リポジトリID: str = Field(..., description="リポジトリID")
    表示名: str = Field(..., description="表示名")
    プロバイダー: リポジトリプロバイダー = Field(..., description="プロバイダー")
    ステータス: リポジトリステータス = Field(..., description="ステータス")
    最終スキャン日時: Optional[datetime] = Field(None, description="最終スキャン日時")
    更新日時: datetime = Field(..., description="更新日時")


class リポジトリ一覧レスポンス(BaseModel):
    """リポジトリ一覧APIのレスポンスモデル"""
    リポジトリ一覧: List[リポジトリ一覧項目] = Field(..., description="リポジトリ一覧")
    総件数: int = Field(..., description="総件数")


class 解析ジョブ開始リクエスト(BaseModel):
    """解析ジョブ開始APIのリクエストモデル"""
    種別: 解析種別 = Field(..., description="解析種別")
    強制実行: bool = Field(default=False, description="既に解析中でも強制実行するか")


class 解析ジョブ開始レスポンス(BaseModel):
    """解析ジョブ開始APIのレスポンスモデル"""
    成功: bool = Field(..., description="開始成功フラグ")
    ジョブID: Optional[str] = Field(None, description="生成されたジョブID")
    メッセージ: str = Field(..., description="結果メッセージ")


def リポジトリIDを生成() -> str:
    """新しいリポジトリIDを生成"""
    return f"repo-{uuid.uuid4().hex[:8]}"


def URLからリポジトリ情報を抽出(URL: str, プロバイダー: リポジトリプロバイダー) -> Dict[str, str]:
    """URLからリポジトリの所有者と名前を抽出"""
    if プロバイダー == リポジトリプロバイダー.GITHUB:
        # GitHub URL パターンの解析
        patterns = [
            r'https://github\.com/([^/]+)/([^/]+)(?:\.git)?/?$',
            r'git@github\.com:([^/]+)/([^/]+)\.git$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, URL)
            if match:
                所有者, リポジトリ名 = match.groups()
                return {
                    "所有者": 所有者,
                    "リポジトリ名": リポジトリ名.replace('.git', ''),
                    "完全名": f"{所有者}/{リポジトリ名.replace('.git', '')}"
                }
    
    elif プロバイダー == リポジトリプロバイダー.CODECOMMIT:
        # CodeCommit URL パターンの解析
        patterns = [
            r'codecommit://([^/]+)$',
            r'codecommit::([^:]+)://([^/]+)$',
            r'https://git-codecommit\.([^.]+)\.amazonaws\.com/v1/repos/([^/]+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, URL)
            if match:
                groups = match.groups()
                if len(groups) == 1:
                    # codecommit://repo-name
                    リポジトリ名 = groups[0]
                    return {
                        "所有者": "codecommit",
                        "リポジトリ名": リポジトリ名,
                        "完全名": f"codecommit/{リポジトリ名}"
                    }
                elif len(groups) == 2:
                    # codecommit::region://repo-name または https://...
                    if 'amazonaws.com' in URL:
                        リージョン, リポジトリ名 = groups
                        return {
                            "所有者": f"codecommit-{リージョン}",
                            "リポジトリ名": リポジトリ名,
                            "完全名": f"codecommit-{リージョン}/{リポジトリ名}"
                        }
                    else:
                        リージョン, リポジトリ名 = groups
                        return {
                            "所有者": f"codecommit-{リージョン}",
                            "リポジトリ名": リポジトリ名,
                            "完全名": f"codecommit-{リージョン}/{リポジトリ名}"
                        }
    
    raise ValueError(f"URLからリポジトリ情報を抽出できませんでした: {URL}")