"""
リポジトリリポジトリ

リポジトリデータのDynamoDB操作を担当するリポジトリクラスです。
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
import os

from api.リポジトリ.DynamoDB基底 import (
    DynamoDB基底リポジトリ, 
    DynamoDB例外, 
    DynamDBアイテム未発見エラー,
    DynamoDB条件チェックエラー
)
from api.モデル.リポジトリ import (
    リポジトリ, 
    リポジトリステータス, 
    リポジトリプロバイダー,
    リポジトリIDを生成
)

logger = logging.getLogger(__name__)


"""
リポジトリリポジトリ

リポジトリデータのDynamoDB操作を担当するリポジトリクラスです。
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
import os

from api.リポジトリ.DynamoDB基底 import (
    DynamoDB基底リポジトリ, 
    DynamoDB例外, 
    DynamDBアイテム未発見エラー,
    DynamoDB条件チェックエラー
)
from api.モデル.リポジトリ import (
    リポジトリ, 
    リポジトリステータス, 
    リポジトリプロバイダー,
    リポジトリIDを生成
)

logger = logging.getLogger(__name__)


class リポジトリリポジトリ(DynamoDB基底リポジトリ):
    """
    リポジトリデータのDynamoDB操作クラス
    
    リポジトリのCRUD（作成、読み取り、更新、削除）操作および、
    ステータスやプロバイダーに基づいた検索機能を提供します。
    """
    
    def __init__(self, 環境: str = None):
        """
        リポジトリリポジトリを初期化します。

        環境変 'ENVIRONMENT' と 'PROJECT_NAME' を使用して、
        接続先のDynamoDBテーブル名を決定します。

        Args:
            環境 (str, optional): 'dev', 'staging', 'prod' などの環境名。
                                  指定されない場合は環境変数から取得します。
        """
        環境 = 環境 or os.environ.get('ENVIRONMENT', 'dev')
        プロジェクト名 = os.environ.get('PROJECT_NAME', 'deepwiki-omr')
        テーブル名 = f"{プロジェクト名}-{環境}-repos"
        
        super().__init__(テーブル名)
        logger.info(f"リポジトリリポジトリを初期化しました: {テーブル名}")

    async def リポジトリを作成(self, プロバイダー: リポジトリプロバイダー, 
                           リモートURL: str, 表示名: str, 
                           デフォルトブランチ: str = "main") -> リポジトリ:
        """
        新しいリポジトリをDynamoDBに作成します。

        指定されたリモートURLが既に存在しないかチェックしてから、
        新しいリポジトリ項目を保存します。

        Args:
            プロバイダー (リポジトリプロバイダー): 'github' または 'codecommit'
            リモートURL (str): リポジトリのクローンURL
            表示名 (str): UIで表示されるリポジトリ名
            デフォルトブランチ (str, optional): デフォルトのブランチ名。デフォルトは "main"。

        Returns:
            リポジトリ: 作成されたリポジトリのデータモデルオブジェクト

        Raises:
            DynamoDB条件チェックエラー: 同じリモートURLのリポジトリが既に存在する場合
            DynamoDB例外: その他のDynamoDB関連エラー
        """
        try:
            # 重複チェック
            if await self.URLでリポジトリを検索(リモートURL):
                raise DynamoDB条件チェックエラー(f"同じURL '{リモートURL}' のリポジトリが既に存在します")
            
            リポジトリID = リポジトリIDを生成()
            現在時刻 = datetime.now()
            
            新リポジトリ = リポジトリ(
                リポジトリID=リポジトリID,
                プロバイダー=プロバイダー,
                リモートURL=リモートURL,
                表示名=表示名,
                デフォルトブランチ=デフォルトブランチ,
                ステータス=リポジトリステータス.READY,
                作成日時=現在時刻,
                更新日時=現在時刻
            )
            
            DynamoDB項目 = 新リポジトリ.DynamoDB項目に変換()
            条件式 = "attribute_not_exists(repo_id)"
            self.アイテムを保存(DynamoDB項目, 条件式)
            
            logger.info(f"リポジトリを作成しました: {リポジトリID} ({表示名})")
            return 新リポジトリ
            
        except DynamoDB条件チェックエラー:
            logger.warning(f"リポジトリ作成失敗（重複）: {リモートURL}")
            raise
        except Exception as e:
            logger.error(f"リポジトリ作成中に予期せぬエラーが発生しました: {e}", exc_info=True)
            raise DynamoDB例外(f"リポジトリの作成に失敗しました: {e}")

    async def リポジトリを取得(self, リポジトリID: str) -> リポジトリ:
        """
        リポジトリIDを使用して単一のリポジトリを取得します。

        Args:
            リポジトリID (str): 取得するリポジトリのID

        Returns:
            リポジトリ: 見つかったリポジトリのデータモデルオブジェクト

        Raises:
            DynamDBアイテム未発見エラー: 指定されたIDのリポジトリが存在しないか、論理削除されている場合
            DynamoDB例外: その他のDynamoDB関連エラー
        """
        try:
            キー = {'repo_id': リポジトリID}
            アイテム = self.アイテムを取得(キー)
            
            if アイテム and not アイテム.get('deleted', False):
                return リポジトリ.DynamoDB項目から作成(アイテム)
            
            raise DynamDBアイテム未発見エラー(f"リポジトリ '{リポジトリID}' が見つかりません")
            
        except DynamDBアイテム未発見エラー:
            raise
        except Exception as e:
            logger.error(f"リポジトリ取得エラー: {e}", exc_info=True)
            raise DynamoDB例外(f"リポジトリ '{リポジトリID}' の取得に失敗しました: {e}")

    async def リポジトリ一覧を取得(self, ステータス: Optional[リポジトリステータス] = None,
                             制限数: Optional[int] = 100) -> List[リポジトリ]:
        """
        リポジトリの一覧を取得します。ステータスによるフィルタリングが可能です。

        Args:
            ステータス (リポジトリステータス, optional): 特定のステータスのリポジトリのみを取得します。
            制限数 (int, optional): 取得する最大件数。デフォルトは 100。

        Returns:
            List[リポジトリ]: リポジトリのリスト
        """
        try:
            if ステータス:
                キー条件式 = Key('status').eq(ステータス.value)
                アイテムリスト = self.クエリ実行(
                    キー条件式=キー条件式,
                    インデックス名='status-index',
                    制限数=制限数,
                    昇順=False
                )
            else:
                フィルター式 = Attr('deleted').ne(True)
                アイテムリスト = self.スキャン実行(
                    フィルター式=フィルター式,
                    制限数=制限数
                )
            
            リポジトリリスト = [リポジトリ.DynamoDB項目から作成(item) for item in アイテムリスト if not item.get('deleted', False)]
            リポジトリリスト.sort(key=lambda r: r.更新日時, reverse=True)
            
            logger.debug(f"リポジトリ一覧を取得しました: {len(リポジトリリスト)}件")
            return リポジトリリスト
            
        except Exception as e:
            logger.error(f"リポジトリ一覧取得エラー: {e}", exc_info=True)
            raise DynamoDB例外(f"リポジトリ一覧の取得に失敗しました: {e}")

    async def リポジトリを更新(self, リポジトリID: str, 
                           更新データ: Dict[str, Any]) -> リポジトリ:
        """
        既存のリポジトリ情報を更新します。

        'updated_at' フィールドは自動的に現在のタイムスタンプに更新されます。

        Args:
            リポジトリID (str): 更新するリポジトリのID
            更新データ (Dict[str, Any]): 更新するフィールドと値の辞書

        Returns:
            リポジトリ: 更新後のリポジトリオブジェクト

        Raises:
            DynamDBアイテム未発見エラー: 更新対象のリポジトリが存在しない場合
            DynamoDB例外: その他のDynamoDB関連エラー
        """
        try:
            キー = {'repo_id': リポジトリID}
            更新データ['updated_at'] = datetime.now().isoformat()
            
            更新式部分 = [f"#{k} = :{k}" for k in 更新データ.keys()]
            式属性名 = {f"#{k}": k for k in 更新データ.keys()}
            式属性値 = {f":{k}": v for k, v in 更新データ.items()}
            
            更新式 = "SET " + ", ".join(更新式部分)
            条件式 = "attribute_exists(repo_id) AND (attribute_not_exists(deleted) OR deleted = :false)"
            式属性値[':false'] = False
            
            更新後アイテム = self.アイテムを更新(
                キー=キー,
                更新式=更新式,
                式属性値=式属性値,
                式属性名=式属性名,
                条件式=条件式
            )
            
            logger.info(f"リポジトリを更新しました: {リポジトリID}")
            return リポジトリ.DynamoDB項目から作成(更新後アイテム)
            
        except DynamoDB条件チェックエラー:
            raise DynamDBアイテム未発見エラー(f"更新対象のリポジトリ '{リポジトリID}' が存在しないか、削除済みです")
        except Exception as e:
            logger.error(f"リポジトリ更新エラー: {e}", exc_info=True)
            raise DynamoDB例外(f"リポジトリ '{リポジトリID}' の更新に失敗しました: {e}")

    async def リポジトリを削除(self, リポジトリID: str, 物理削除: bool = False) -> bool:
        """
        リポジトリを削除します。論理削除または物理削除を選択できます。

        Args:
            リポジトリID (str): 削除するリポジトリのID
            物理削除 (bool, optional): Trueの場合、DBから完全に削除します。
                                     Falseの場合、'deleted'フラグを立てます。デフォルトは False。

        Returns:
            bool: 削除が成功した場合は True

        Raises:
            DynamoDB例外: 削除処理中にエラーが発生した場合
        """
        try:
            キー = {'repo_id': リポジトリID}
            
            if 物理削除:
                self.アイテムを削除(キー, 条件式="attribute_exists(repo_id)")
                logger.info(f"リポジトリを物理削除しました: {リポジトリID}")
            else:
                await self.リポジトリを更新(リポジトリID, {'deleted': True})
                logger.info(f"リポジトリを論理削除しました: {リポジトリID}")
            
            return True
            
        except DynamDBアイテム未発見エラー:
            logger.warning(f"削除対象のリポジトリが存在しません: {リポジトリID}")
            return False
        except Exception as e:
            logger.error(f"リポジトリ削除エラー: {e}", exc_info=True)
            raise DynamoDB例外(f"リポジトリ '{リポジトリID}' の削除に失敗しました: {e}")

    async def ステータスを更新(self, リポジトリID: str, 
                           新ステータス: リポジトリステータス,
                           最終スキャンSHA: Optional[str] = None) -> bool:
        """
        リポジトリのステータスを更新します。

        スキャンSHAが提供された場合、最終スキャン日時も更新します。

        Args:
            リポジトリID (str): ステータスを更新するリポジトリのID
            新ステータス (リポジトリステータス): 新しいステータス
            最終スキャンSHA (str, optional): 最新のコミットSHA

        Returns:
            bool: 更新が成功した場合は True
        """
        try:
            更新データ = {'status': 新ステータス.value}
            if 最終スキャンSHA:
                更新データ['last_scan_sha'] = 最終スキャンSHA
                更新データ['last_scan_at'] = datetime.now().isoformat()
            
            await self.リポジトリを更新(リポジトリID, 更新データ)
            logger.info(f"リポジトリステータスを更新しました: {リポジトリID} -> {新ステータス.value}")
            return True
            
        except DynamDBアイテム未発見エラー:
            logger.warning(f"ステータス更新対象のリポジトリが存在しません: {リポジトリID}")
            return False
        except Exception as e:
            logger.error(f"ステータス更新エラー: {e}", exc_info=True)
            raise DynamoDB例外(f"ステータス '{リポジトリID}' の更新に失敗しました: {e}")

    async def URLでリポジトリを検索(self, リモートURL: str) -> Optional[リポジトリ]:
        """
        リモートURLを使用してリポジトリを検索します。

        この操作はGSIを使用しないため、大規模なテーブルではパフォーマンスが低下する可能性があります。

        Args:
            リモートURL (str): 検索するリポジトリのURL

        Returns:
            Optional[リポジトリ]: 見つかったリポジトリオブジェクト。存在しない場合は None。
        """
        try:
            フィルター式 = Attr('remote_url').eq(リモートURL) & Attr('deleted').ne(True)
            アイテムリスト = self.スキャン実行(フィルター式=フィルター式, 制限数=1)
            
            return リポジトリ.DynamoDB項目から作成(アイテムリスト[0]) if アイテムリスト else None
            
        except Exception as e:
            logger.error(f"URL検索エラー: {e}", exc_info=True)
            raise DynamoDB例外(f"URL '{リモートURL}' でのリポジトリ検索に失敗しました: {e}")

    async def プロバイダー別リポジトリ数を取得(self) -> Dict[str, int]:
        """
        プロバイダーごとのリポジトリ数を集計します。

        Returns:
            Dict[str, int]: {'github': 10, 'codecommit': 5} のような辞書
        """
        try:
            フィルター式 = Attr('deleted').ne(True)
            アイテムリスト = self.スキャン実行(フィルター式=フィルター式)
            
            プロバイダー別数 = {}
            for item in アイテムリスト:
                provider = item.get('provider', 'unknown')
                プロバイダー別数[provider] = プロバイダー別数.get(provider, 0) + 1
            
            logger.debug(f"プロバイダー別リポジトリ数: {プロバイダー別数}")
            return プロバイダー別数
            
        except Exception as e:
            logger.error(f"プロバイダー別数取得エラー: {e}", exc_info=True)
            raise DynamoDB例外("プロバイダー別リポジトリ数の取得に失敗しました")

    async def ステータス別リポジトリ数を取得(self) -> Dict[str, int]:
        """
        ステータスごとのリポジトリ数を集計します。

        'status-index' GSI を使用して効率的に集計します。

        Returns:
            Dict[str, int]: {'READY': 20, 'PARSING': 2} のような辞書
        """
        try:
            ステータス別数 = {}
            for status in リポジトリステータス:
                キー条件式 = Key('status').eq(status.value)
                アイテムリスト = self.クエリ実行(
                    キー条件式=キー条件式,
                    インデックス名='status-index'
                )
                有効数 = sum(1 for item in アイテムリスト if not item.get('deleted', False))
                ステータス別数[status.value] = 有効数
            
            logger.debug(f"ステータス別リポジトリ数: {ステータス別数}")
            return ステータス別数
            
        except Exception as e:
            logger.error(f"ステータス別数取得エラー: {e}", exc_info=True)
            raise DynamoDB例外("ステータス別リポジトリ数の取得に失敗しました")

    async def 最近更新されたリポジトリを取得(self, 件数: int = 10) -> List[リポジトリ]:
        """
        最近更新されたリポジトリを更新日時の降順で取得します。

        Args:
            件数 (int, optional): 取得する件数。デフォルトは 10。

        Returns:
            List[リポジトリ]: 最近更新されたリポジトリのリスト
        """
        try:
            フィルター式 = Attr('deleted').ne(True)
            アイテムリスト = self.スキャン実行(フィルター式=フィルター式)
            
            リポジトリリスト = [リポジトリ.DynamoDB項目から作成(item) for item in アイテムリスト]
            リポジトリリスト.sort(key=lambda r: r.更新日時, reverse=True)
            
            結果 = リポジトリリスト[:件数]
            logger.debug(f"最近更新されたリポジトリを取得しました: {len(結果)}件")
            return 結果
            
        except Exception as e:
            logger.error(f"最近更新リポジトリ取得エラー: {e}", exc_info=True)
            raise DynamoDB例外("最近更新されたリポジトリの取得に失敗しました")


    async def リポジトリを作成(self, プロバイダー: リポジトリプロバイダー, 
                           リモートURL: str, 表示名: str, 
                           デフォルトブランチ: str = "main") -> リポジトリ:
        """
        新しいリポジトリを作成
        
        Args:
            プロバイダー: リポジトリプロバイダー
            リモートURL: リモートURL
            表示名: 表示名
            デフォルトブランチ: デフォルトブランチ
            
        Returns:
            作成されたリポジトリ
            
        Raises:
            DynamoDB条件チェックエラー: 同じURLのリポジトリが既に存在する場合
        """
        try:
            # 重複チェック
            既存リポジトリ = await self.URLでリポジトリを検索(リモートURL)
            if 既存リポジトリ:
                raise DynamoDB条件チェックエラー(f"同じURL '{リモートURL}' のリポジトリが既に存在します")
            
            # 新しいリポジトリを作成
            リポジトリID = リポジトリIDを生成()
            現在時刻 = datetime.now()
            
            新リポジトリ = リポジトリ(
                リポジトリID=リポジトリID,
                プロバイダー=プロバイダー,
                リモートURL=リモートURL,
                表示名=表示名,
                デフォルトブランチ=デフォルトブランチ,
                ステータス=リポジトリステータス.READY,
                作成日時=現在時刻,
                更新日時=現在時刻
            )
            
            # DynamoDBに保存
            DynamoDB項目 = 新リポジトリ.DynamoDB項目に変換()
            
            # 条件付き保存（リポジトリIDが存在しない場合のみ）
            条件式 = "attribute_not_exists(repo_id)"
            self.アイテムを保存(DynamoDB項目, 条件式)
            
            logger.info(f"リポジトリを作成しました: {リポジトリID} ({表示名})")
            return 新リポジトリ
            
        except DynamoDB条件チェックエラー:
            raise
        except Exception as e:
            logger.error(f"リポジトリ作成エラー: {e}")
            raise DynamoDB例外(f"リポジトリの作成に失敗しました: {e}")

    async def リポジトリを取得(self, リポジトリID: str) -> Optional[リポジトリ]:
        """
        リポジトリIDでリポジトリを取得
        
        Args:
            リポジトリID: リポジトリID
            
        Returns:
            リポジトリ（存在しない場合はNone）
        """
        try:
            キー = {'repo_id': リポジトリID}
            アイテム = self.アイテムを取得(キー)
            
            if アイテム and not アイテム.get('deleted', False):
                return リポジトリ.DynamoDB項目から作成(アイテム)
            
            return None
            
        except Exception as e:
            logger.error(f"リポジトリ取得エラー: {e}")
            raise DynamoDB例外(f"リポジトリの取得に失敗しました: {e}")

    async def リポジトリ一覧を取得(self, ステータス: Optional[リポジトリステータス] = None,
                             制限数: Optional[int] = None) -> List[リポジトリ]:
        """
        リポジトリ一覧を取得
        
        Args:
            ステータス: フィルターするステータス（オプション）
            制限数: 取得件数制限（オプション）
            
        Returns:
            リポジトリのリスト
        """
        try:
            if ステータス:
                # ステータス別にGSIを使用してクエリ
                キー条件式 = Key('status').eq(ステータス.value)
                アイテムリスト = self.クエリ実行(
                    キー条件式=キー条件式,
                    インデックス名='status-index',
                    制限数=制限数,
                    昇順=False  # 更新日時の降順
                )
            else:
                # 全件スキャン（削除されていないもののみ）
                フィルター式 = Attr('deleted').ne(True)
                アイテムリスト = self.スキャン実行(
                    フィルター式=フィルター式,
                    制限数=制限数
                )
            
            # リポジトリオブジェクトに変換
            リポジトリリスト = []
            for アイテム in アイテムリスト:
                if not アイテム.get('deleted', False):
                    リポジトリリスト.append(リポジトリ.DynamoDB項目から作成(アイテム))
            
            # 更新日時で降順ソート
            リポジトリリスト.sort(key=lambda r: r.更新日時, reverse=True)
            
            logger.debug(f"リポジトリ一覧を取得しました: {len(リポジトリリスト)}件")
            return リポジトリリスト
            
        except Exception as e:
            logger.error(f"リポジトリ一覧取得エラー: {e}")
            raise DynamoDB例外(f"リポジトリ一覧の取得に失敗しました: {e}")

    async def リポジトリを更新(self, リポジトリID: str, 
                           更新データ: Dict[str, Any]) -> Optional[リポジトリ]:
        """
        リポジトリを更新
        
        Args:
            リポジトリID: リポジトリID
            更新データ: 更新するデータ
            
        Returns:
            更新後のリポジトリ（存在しない場合はNone）
        """
        try:
            キー = {'repo_id': リポジトリID}
            
            # 更新式を構築
            更新式部分 = []
            式属性値 = {}
            式属性名 = {}
            
            # 更新日時を自動設定
            更新データ['updated_at'] = datetime.now().isoformat()
            
            for フィールド名, 値 in 更新データ.items():
                属性名キー = f"#{フィールド名}"
                属性値キー = f":{フィールド名}"
                
                更新式部分.append(f"{属性名キー} = {属性値キー}")
                式属性名[属性名キー] = フィールド名
                式属性値[属性値キー] = 値
            
            更新式 = "SET " + ", ".join(更新式部分)
            
            # 条件式（削除されていないアイテムのみ更新）
            条件式 = "attribute_exists(repo_id) AND (attribute_not_exists(deleted) OR deleted = :false)"
            式属性値[':false'] = False
            
            更新後アイテム = self.アイテムを更新(
                キー=キー,
                更新式=更新式,
                式属性値=式属性値,
                式属性名=式属性名,
                条件式=条件式
            )
            
            logger.info(f"リポジトリを更新しました: {リポジトリID}")
            return リポジトリ.DynamoDB項目から作成(更新後アイテム)
            
        except DynamoDB条件チェックエラー:
            logger.warning(f"リポジトリが存在しないか削除済みです: {リポジトリID}")
            return None
        except Exception as e:
            logger.error(f"リポジトリ更新エラー: {e}")
            raise DynamoDB例外(f"リポジトリの更新に失敗しました: {e}")

    async def リポジトリを削除(self, リポジトリID: str, 物理削除: bool = False) -> bool:
        """
        リポジトリを削除
        
        Args:
            リポジトリID: リポジトリID
            物理削除: 物理削除フラグ（True: 物理削除、False: 論理削除）
            
        Returns:
            削除成功フラグ
        """
        try:
            キー = {'repo_id': リポジトリID}
            
            if 物理削除:
                # 物理削除
                条件式 = "attribute_exists(repo_id)"
                削除成功 = self.アイテムを削除(キー, 条件式)
                logger.info(f"リポジトリを物理削除しました: {リポジトリID}")
            else:
                # 論理削除
                更新式 = "SET deleted = :true, updated_at = :updated_at"
                式属性値 = {
                    ':true': True,
                    ':updated_at': datetime.now().isoformat()
                }
                条件式 = "attribute_exists(repo_id) AND (attribute_not_exists(deleted) OR deleted = :false)"
                式属性値[':false'] = False
                
                self.アイテムを更新(
                    キー=キー,
                    更新式=更新式,
                    式属性値=式属性値,
                    条件式=条件式
                )
                削除成功 = True
                logger.info(f"リポジトリを論理削除しました: {リポジトリID}")
            
            return 削除成功
            
        except DynamoDB条件チェックエラー:
            logger.warning(f"削除対象のリポジトリが存在しません: {リポジトリID}")
            return False
        except Exception as e:
            logger.error(f"リポジトリ削除エラー: {e}")
            raise DynamoDB例外(f"リポジトリの削除に失敗しました: {e}")

    async def ステータスを更新(self, リポジトリID: str, 
                           新ステータス: リポジトリステータス,
                           最終スキャンSHA: Optional[str] = None) -> bool:
        """
        リポジトリのステータスを更新
        
        Args:
            リポジトリID: リポジトリID
            新ステータス: 新しいステータス
            最終スキャンSHA: 最終スキャンSHA（オプション）
            
        Returns:
            更新成功フラグ
        """
        try:
            更新データ = {
                'status': 新ステータス.value
            }
            
            if 最終スキャンSHA:
                更新データ['last_scan_sha'] = 最終スキャンSHA
                更新データ['last_scan_at'] = datetime.now().isoformat()
            
            更新後リポジトリ = await self.リポジトリを更新(リポジトリID, 更新データ)
            
            if 更新後リポジトリ:
                logger.info(f"リポジトリステータスを更新しました: {リポジトリID} -> {新ステータス.value}")
                return True
            else:
                logger.warning(f"ステータス更新対象のリポジトリが存在しません: {リポジトリID}")
                return False
                
        except Exception as e:
            logger.error(f"ステータス更新エラー: {e}")
            raise DynamoDB例外(f"ステータスの更新に失敗しました: {e}")

    async def URLでリポジトリを検索(self, リモートURL: str) -> Optional[リポジトリ]:
        """
        リモートURLでリポジトリを検索
        
        Args:
            リモートURL: 検索するリモートURL
            
        Returns:
            見つかったリポジトリ（存在しない場合はNone）
        """
        try:
            # 全件スキャンでURL検索（GSIがないため）
            フィルター式 = Attr('remote_url').eq(リモートURL) & Attr('deleted').ne(True)
            アイテムリスト = self.スキャン実行(フィルター式=フィルター式, 制限数=1)
            
            if アイテムリスト:
                return リポジトリ.DynamoDB項目から作成(アイテムリスト[0])
            
            return None
            
        except Exception as e:
            logger.error(f"URL検索エラー: {e}")
            raise DynamoDB例外(f"URLでのリポジトリ検索に失敗しました: {e}")

    async def プロバイダー別リポジトリ数を取得(self) -> Dict[str, int]:
        """
        プロバイダー別のリポジトリ数を取得
        
        Returns:
            プロバイダー別リポジトリ数の辞書
        """
        try:
            # 削除されていないリポジトリをスキャン
            フィルター式 = Attr('deleted').ne(True)
            アイテムリスト = self.スキャン実行(フィルター式=フィルター式)
            
            プロバイダー別数 = {}
            for アイテム in アイテムリスト:
                プロバイダー = アイテム.get('provider', 'unknown')
                プロバイダー別数[プロバイダー] = プロバイダー別数.get(プロバイダー, 0) + 1
            
            logger.debug(f"プロバイダー別リポジトリ数: {プロバイダー別数}")
            return プロバイダー別数
            
        except Exception as e:
            logger.error(f"プロバイダー別数取得エラー: {e}")
            raise DynamoDB例外(f"プロバイダー別リポジトリ数の取得に失敗しました: {e}")

    async def ステータス別リポジトリ数を取得(self) -> Dict[str, int]:
        """
        ステータス別のリポジトリ数を取得
        
        Returns:
            ステータス別リポジトリ数の辞書
        """
        try:
            ステータス別数 = {}
            
            # 各ステータスでGSIクエリを実行
            for ステータス in リポジトリステータス:
                キー条件式 = Key('status').eq(ステータス.value)
                アイテムリスト = self.クエリ実行(
                    キー条件式=キー条件式,
                    インデックス名='status-index'
                )
                
                # 削除されていないもののみカウント
                有効数 = sum(1 for アイテム in アイテムリスト if not アイテム.get('deleted', False))
                ステータス別数[ステータス.value] = 有効数
            
            logger.debug(f"ステータス別リポジトリ数: {ステータス別数}")
            return ステータス別数
            
        except Exception as e:
            logger.error(f"ステータス別数取得エラー: {e}")
            raise DynamoDB例外(f"ステータス別リポジトリ数の取得に失敗しました: {e}")

    async def 最近更新されたリポジトリを取得(self, 件数: int = 10) -> List[リポジトリ]:
        """
        最近更新されたリポジトリを取得
        
        Args:
            件数: 取得件数
            
        Returns:
            最近更新されたリポジトリのリスト
        """
        try:
            # 削除されていないリポジトリをスキャン
            フィルター式 = Attr('deleted').ne(True)
            アイテムリスト = self.スキャン実行(フィルター式=フィルター式)
            
            # リポジトリオブジェクトに変換
            リポジトリリスト = [リポジトリ.DynamoDB項目から作成(アイテム) for アイテム in アイテムリスト]
            
            # 更新日時で降順ソートして指定件数を取得
            リポジトリリスト.sort(key=lambda r: r.更新日時, reverse=True)
            
            結果 = リポジトリリスト[:件数]
            logger.debug(f"最近更新されたリポジトリを取得しました: {len(結果)}件")
            return 結果
            
        except Exception as e:
            logger.error(f"最近更新リポジトリ取得エラー: {e}")
            raise DynamoDB例外(f"最近更新されたリポジトリの取得に失敗しました: {e}")