"""
DynamoDB基底クラス

DynamoDB操作の共通機能を提供する基底クラスです。
"""

import boto3
import logging
from typing import Dict, Any, List, Optional, Type, TypeVar
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime
import os

# ログ設定
logger = logging.getLogger(__name__)

# 型変数
T = TypeVar('T')


class DynamoDB例外(Exception):
    """DynamoDB操作に関する例外の基底クラス"""
    pass


class DynamoDB接続エラー(DynamoDB例外):
    """DynamoDB接続エラー"""
    pass


class DynamDBアイテム未発見エラー(DynamoDB例外):
    """アイテムが見つからない場合のエラー"""
    pass


class DynamoDB条件チェックエラー(DynamoDB例外):
    """条件チェック失敗エラー"""
    pass


class DynamoDB基底リポジトリ:
    """
    DynamoDB操作の基底クラス
    
    共通的なDynamoDB操作を提供します。
    """
    
    def __init__(self, テーブル名: str, リージョン: str = None):
        """
        初期化
        
        Args:
            テーブル名: DynamoDBテーブル名
            リージョン: AWSリージョン（環境変数から取得可能）
        """
        self.テーブル名 = テーブル名
        self.リージョン = リージョン or os.environ.get('AWS_DEFAULT_REGION', 'ap-northeast-1')
        
        try:
            # DynamoDBクライアントの初期化
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=self.リージョン
            )
            self.テーブル = self.dynamodb.Table(self.テーブル名)
            
            # テーブルの存在確認
            self.テーブル.load()
            logger.info(f"DynamoDBテーブル '{self.テーブル名}' に接続しました")
            
        except ClientError as e:
            エラーコード = e.response['Error']['Code']
            if エラーコード == 'ResourceNotFoundException':
                raise DynamoDB接続エラー(f"テーブル '{self.テーブル名}' が見つかりません")
            else:
                raise DynamoDB接続エラー(f"DynamoDB接続エラー: {e}")
        except BotoCoreError as e:
            raise DynamoDB接続エラー(f"AWS設定エラー: {e}")
        except Exception as e:
            raise DynamoDB接続エラー(f"予期しないエラー: {e}")

    def アイテムを取得(self, キー: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        アイテムを取得
        
        Args:
            キー: プライマリキー
            
        Returns:
            取得したアイテム（存在しない場合はNone）
        """
        try:
            レスポンス = self.テーブル.get_item(Key=キー)
            return レスポンス.get('Item')
            
        except ClientError as e:
            logger.error(f"アイテム取得エラー: {e}")
            raise DynamoDB例外(f"アイテム取得に失敗しました: {e}")

    def アイテムを保存(self, アイテム: Dict[str, Any], 条件式: str = None) -> bool:
        """
        アイテムを保存
        
        Args:
            アイテム: 保存するアイテム
            条件式: 条件式（オプション）
            
        Returns:
            保存成功フラグ
        """
        try:
            保存パラメータ = {'Item': アイテム}
            
            if 条件式:
                保存パラメータ['ConditionExpression'] = 条件式
            
            self.テーブル.put_item(**保存パラメータ)
            logger.debug(f"アイテムを保存しました: {アイテム.get('id', 'unknown')}")
            return True
            
        except ClientError as e:
            エラーコード = e.response['Error']['Code']
            if エラーコード == 'ConditionalCheckFailedException':
                raise DynamoDB条件チェックエラー("条件チェックに失敗しました")
            else:
                logger.error(f"アイテム保存エラー: {e}")
                raise DynamoDB例外(f"アイテム保存に失敗しました: {e}")

    def アイテムを更新(self, キー: Dict[str, Any], 更新式: str, 
                    式属性値: Dict[str, Any] = None, 
                    式属性名: Dict[str, str] = None,
                    条件式: str = None) -> Dict[str, Any]:
        """
        アイテムを更新
        
        Args:
            キー: プライマリキー
            更新式: 更新式
            式属性値: 式で使用する属性値
            式属性名: 式で使用する属性名
            条件式: 条件式（オプション）
            
        Returns:
            更新後のアイテム
        """
        try:
            更新パラメータ = {
                'Key': キー,
                'UpdateExpression': 更新式,
                'ReturnValues': 'ALL_NEW'
            }
            
            if 式属性値:
                更新パラメータ['ExpressionAttributeValues'] = 式属性値
            if 式属性名:
                更新パラメータ['ExpressionAttributeNames'] = 式属性名
            if 条件式:
                更新パラメータ['ConditionExpression'] = 条件式
            
            レスポンス = self.テーブル.update_item(**更新パラメータ)
            return レスポンス['Attributes']
            
        except ClientError as e:
            エラーコード = e.response['Error']['Code']
            if エラーコード == 'ConditionalCheckFailedException':
                raise DynamoDB条件チェックエラー("条件チェックに失敗しました")
            else:
                logger.error(f"アイテム更新エラー: {e}")
                raise DynamoDB例外(f"アイテム更新に失敗しました: {e}")

    def アイテムを削除(self, キー: Dict[str, Any], 条件式: str = None) -> bool:
        """
        アイテムを削除
        
        Args:
            キー: プライマリキー
            条件式: 条件式（オプション）
            
        Returns:
            削除成功フラグ
        """
        try:
            削除パラメータ = {'Key': キー}
            
            if 条件式:
                削除パラメータ['ConditionExpression'] = 条件式
            
            self.テーブル.delete_item(**削除パラメータ)
            logger.debug(f"アイテムを削除しました: {キー}")
            return True
            
        except ClientError as e:
            エラーコード = e.response['Error']['Code']
            if エラーコード == 'ConditionalCheckFailedException':
                raise DynamoDB条件チェックエラー("条件チェックに失敗しました")
            else:
                logger.error(f"アイテム削除エラー: {e}")
                raise DynamoDB例外(f"アイテム削除に失敗しました: {e}")

    def クエリ実行(self, キー条件式: str, 式属性値: Dict[str, Any] = None,
                 式属性名: Dict[str, str] = None, フィルター式: str = None,
                 インデックス名: str = None, 制限数: int = None,
                 昇順: bool = True) -> List[Dict[str, Any]]:
        """
        クエリを実行
        
        Args:
            キー条件式: キー条件式
            式属性値: 式で使用する属性値
            式属性名: 式で使用する属性名
            フィルター式: フィルター式（オプション）
            インデックス名: GSIインデックス名（オプション）
            制限数: 取得件数制限（オプション）
            昇順: ソート順（True: 昇順、False: 降順）
            
        Returns:
            クエリ結果のアイテムリスト
        """
        try:
            クエリパラメータ = {
                'KeyConditionExpression': キー条件式,
                'ScanIndexForward': 昇順
            }
            
            if 式属性値:
                クエリパラメータ['ExpressionAttributeValues'] = 式属性値
            if 式属性名:
                クエリパラメータ['ExpressionAttributeNames'] = 式属性名
            if フィルター式:
                クエリパラメータ['FilterExpression'] = フィルター式
            if インデックス名:
                クエリパラメータ['IndexName'] = インデックス名
            if 制限数:
                クエリパラメータ['Limit'] = 制限数
            
            レスポンス = self.テーブル.query(**クエリパラメータ)
            return レスポンス['Items']
            
        except ClientError as e:
            logger.error(f"クエリ実行エラー: {e}")
            raise DynamoDB例外(f"クエリ実行に失敗しました: {e}")

    def スキャン実行(self, フィルター式: str = None, 式属性値: Dict[str, Any] = None,
                   式属性名: Dict[str, str] = None, 制限数: int = None) -> List[Dict[str, Any]]:
        """
        スキャンを実行
        
        Args:
            フィルター式: フィルター式（オプション）
            式属性値: 式で使用する属性値
            式属性名: 式で使用する属性名
            制限数: 取得件数制限（オプション）
            
        Returns:
            スキャン結果のアイテムリスト
        """
        try:
            スキャンパラメータ = {}
            
            if フィルター式:
                スキャンパラメータ['FilterExpression'] = フィルター式
            if 式属性値:
                スキャンパラメータ['ExpressionAttributeValues'] = 式属性値
            if 式属性名:
                スキャンパラメータ['ExpressionAttributeNames'] = 式属性名
            if 制限数:
                スキャンパラメータ['Limit'] = 制限数
            
            レスポンス = self.テーブル.scan(**スキャンパラメータ)
            return レスポンス['Items']
            
        except ClientError as e:
            logger.error(f"スキャン実行エラー: {e}")
            raise DynamoDB例外(f"スキャン実行に失敗しました: {e}")

    def バッチ書き込み(self, アイテムリスト: List[Dict[str, Any]], 
                     削除キーリスト: List[Dict[str, Any]] = None) -> bool:
        """
        バッチ書き込み
        
        Args:
            アイテムリスト: 保存するアイテムのリスト
            削除キーリスト: 削除するキーのリスト（オプション）
            
        Returns:
            書き込み成功フラグ
        """
        try:
            with self.テーブル.batch_writer() as バッチ:
                # アイテムの保存
                for アイテム in アイテムリスト:
                    バッチ.put_item(Item=アイテム)
                
                # アイテムの削除
                if 削除キーリスト:
                    for キー in 削除キーリスト:
                        バッチ.delete_item(Key=キー)
            
            logger.info(f"バッチ書き込み完了: 保存={len(アイテムリスト)}, 削除={len(削除キーリスト or [])}")
            return True
            
        except ClientError as e:
            logger.error(f"バッチ書き込みエラー: {e}")
            raise DynamoDB例外(f"バッチ書き込みに失敗しました: {e}")

    def 現在時刻を取得(self) -> str:
        """現在時刻をISO形式で取得"""
        return datetime.now().isoformat()

    def テーブル情報を取得(self) -> Dict[str, Any]:
        """テーブル情報を取得"""
        try:
            return {
                'テーブル名': self.テーブル.table_name,
                'テーブル状態': self.テーブル.table_status,
                'アイテム数': self.テーブル.item_count,
                'テーブルサイズ': self.テーブル.table_size_bytes,
                '作成日時': self.テーブル.creation_date_time
            }
        except Exception as e:
            logger.error(f"テーブル情報取得エラー: {e}")
            return {}