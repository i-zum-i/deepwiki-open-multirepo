"""
リポジトリ管理APIエンドポイント

リポジトリのCRUD操作を提供するためのFastAPIルーターです。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional

from api.リポジトリ.リポジトリリポジトリ import リポジトリリポジトリ
from api.モデル.リポジトリ import (
    リポジトリ,
    リポジトリ登録リクエスト,
    リポジトリ登録レスポンス,
    リポジトリ詳細,
    リポジトリ一覧レスポンス,
    リポジトリ一覧項目,
    解析ジョブ開始リクエスト,
    解析ジョブ開始レスポンス
)
from api.リポジトリ.DynamoDB基底 import DynamDBアイテム未発見エラー, DynamoDB条件チェックエラー

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
    responses={404: {"description": "Not found"}},
)

# DI (Dependency Injection) のためのヘルパー関数
def get_repository_repo() -> リポジトリリポジトリ:
    """リポジトリリポジトリのインスタンスを取得します"""
    return リポジトリリポジトリ()

@router.post(
    "/",
    response_model=リポジトリ登録レスポンス,
    status_code=status.HTTP_201_CREATED,
    summary="新規リポジトリの登録",
    description="新しいリポジトリをシステムに登録します。",
)
async def register_repository(
    repo_request: リポジトリ登録リクエスト = Body(...),
    repo: リポジトリリポジトリ = Depends(get_repository_repo)
):
    """
    新しいリポジトリを登録します。

    - **repo_request**: 登録するリポジトリの情報。
    - **repo**: DIによるリポジトリリポジトリのインスタンス。
    """
    try:
        new_repo = await repo.リポジトリを作成(
            プロバイダー=repo_request.プロバイダー,
            リモートURL=repo_request.リモートURL,
            表示名=repo_request.表示名,
            デフォルトブランチ=repo_request.デフォルトブランチ
        )
        return リポジトリ登録レスポンス(
            成功=True,
            リポジトリID=new_repo.リポジトリID,
            メッセージ="リポジトリが正常に登録されました。"
        )
    except DynamoDB条件チェックエラー as e:
        logger.warning(f"リポジトリ登録失敗（重複）: {repo_request.リモートURL}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"リポジトリ登録エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リポジトリの登録中に内部エラーが発生しました。",
        )

@router.get(
    "/",
    response_model=リポジトリ一覧レスポンス,
    summary="リポジトリ一覧の取得",
    description="登録されているリポジトリの一覧を取得します。",
)
async def get_all_repositories(
    repo: リポジトリリポジトリ = Depends(get_repository_repo),
    limit: int = 100
):
    """
    登録済みのリポジトリ一覧を取得します。
    """
    try:
        repos = await repo.リポジトリ一覧を取得(制限数=limit)
        total_count = len(repos)
        
        items = [
            リポジトリ一覧項目(
                リポジトリID=r.リポジトリID,
                表示名=r.表示名,
                プロバイダー=r.プロバイダー,
                ステータス=r.ステータス,
                最終スキャン日時=r.最終スキャン日時,
                更新日時=r.更新日時
            ) for r in repos
        ]
        
        return リポジトリ一覧レスポンス(リポジトリ一覧=items, 総件数=total_count)
    except Exception as e:
        logger.error(f"リポジトリ一覧取得エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リポジトリ一覧の取得中にエラーが発生しました。",
        )

@router.get(
    "/{repo_id}",
    response_model=リポジトリ詳細,
    summary="リポジトリ詳細の取得",
    description="指定されたIDのリポジトリ詳細情報を取得します。",
)
async def get_repository_details(
    repo_id: str,
    repo: リポジトリリポジトリ = Depends(get_repository_repo)
):
    """
    指定されたリポジトリIDの詳細情報を取得します。
    """
    try:
        repo_data = await repo.リポジトリを取得(repo_id)
        # TODO: ページ数や最新ジョブ情報を取得するロジックを追加
        return リポジトリ詳細(
            **repo_data.model_dump(),
            ページ数=0, # 仮
            最新ジョブ=None # 仮
        )
    except DynamDBアイテム未発見エラー:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="リポジトリが見つかりません")
    except Exception as e:
        logger.error(f"リポジトリ詳細取得エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リポジトリ詳細の取得中にエラーが発生しました。",
        )

@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="リポジトリの削除",
    description="指定されたIDのリポジトリを削除します（論理削除）。",
)
async def delete_repository(
    repo_id: str,
    repo: リポジトリリポジトリ = Depends(get_repository_repo)
):
    """
    指定されたリポジトリIDを論理削除します。
    """
    try:
        success = await repo.リポジトリを削除(repo_id, 物理削除=False)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="削除対象のリポジトリが見つかりません")
    except Exception as e:
        logger.error(f"リポジトリ削除エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リポジトリの削除中にエラーが発生しました。",
        )

# TODO: PUT (更新) エンドポイントの実装
# TODO: 解析開始エンドポイントの実装
