# テスト標準

## 概要

DeepWiki-OMRプロジェクトにおけるテスト戦略、テスト手法、品質保証の標準を定義します。

## テスト戦略

### テストピラミッド
```
        E2E テスト (10%)
       ┌─────────────────┐
      │  ユーザーシナリオ  │
     └─────────────────┘
    
    統合テスト (20%)
   ┌─────────────────────┐
  │   API・サービス連携   │
 └─────────────────────┘

単体テスト (70%)
┌─────────────────────────┐
│  関数・クラス・コンポーネント │
└─────────────────────────┘
```

### テストレベル定義

#### 単体テスト (Unit Test)
- **対象**: 個別の関数、クラス、コンポーネント
- **目的**: ロジックの正確性確認
- **実行頻度**: コミット毎
- **カバレッジ目標**: 80%以上

#### 統合テスト (Integration Test)
- **対象**: API間連携、外部サービス連携
- **目的**: インターフェースの動作確認
- **実行頻度**: プルリクエスト毎
- **カバレッジ目標**: 主要パス100%

#### E2Eテスト (End-to-End Test)
- **対象**: ユーザーシナリオ全体
- **目的**: システム全体の動作確認
- **実行頻度**: リリース前
- **カバレッジ目標**: 重要シナリオ100%

## テスト実装標準

### 単体テスト

#### Python (FastAPI)
```python
import pytest
from unittest.mock import Mock, patch
from api.サービス.リポジトリ管理 import リポジトリ管理サービス

class Testリポジトリ管理サービス:
    """リポジトリ管理サービスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.サービス = リポジトリ管理サービス()
    
    def test_GitHubリポジトリ登録_正常系(self):
        """GitHubリポジトリの正常登録をテスト"""
        # Arrange (準備)
        プロバイダー = "github"
        リモートURL = "https://github.com/test/repo.git"
        表示名 = "テストリポジトリ"
        
        # Act (実行)
        結果 = self.サービス.リポジトリを登録(プロバイダー, リモートURL, 表示名)
        
        # Assert (検証)
        assert 結果.成功 == True
        assert 結果.リポジトリID is not None
        assert 結果.メッセージ == "リポジトリが正常に登録されました"
    
    def test_無効なURL_異常系(self):
        """無効なURLでの登録失敗をテスト"""
        # Arrange
        プロバイダー = "github"
        無効なURL = "invalid-url"
        表示名 = "テストリポジトリ"
        
        # Act & Assert
        with pytest.raises(ValueError) as 例外情報:
            self.サービス.リポジトリを登録(プロバイダー, 無効なURL, 表示名)
        
        assert "無効なURL形式です" in str(例外情報.value)
    
    @patch('api.サービス.リポジトリ管理.DynamoDBクライアント')
    def test_データベースエラー_異常系(self, モックDB):
        """データベースエラー時の処理をテスト"""
        # Arrange
        モックDB.put_item.side_effect = Exception("DB接続エラー")
        
        # Act & Assert
        with pytest.raises(Exception) as 例外情報:
            self.サービス.リポジトリを登録("github", "https://github.com/test/repo.git", "テスト")
        
        assert "DB接続エラー" in str(例外情報.value)
```

#### TypeScript (React)
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { リポジトリ登録フォーム } from '@/コンポーネント/リポジトリ登録フォーム';
import { APIクライアント } from '@/ユーティリティ/APIクライアント';

// モック設定
jest.mock('@/ユーティリティ/APIクライアント');
const モックAPIクライアント = APIクライアント as jest.Mocked<typeof APIクライアント>;

describe('リポジトリ登録フォーム', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('正常な入力でリポジトリが登録される', async () => {
    // Arrange
    const 登録成功レスポンス = {
      成功: true,
      リポジトリID: 'repo-123',
      メッセージ: '登録が完了しました'
    };
    モックAPIクライアント.リポジトリを登録.mockResolvedValue(登録成功レスポンス);

    render(<リポジトリ登録フォーム />);

    // Act
    fireEvent.change(screen.getByLabelText('プロバイダー'), {
      target: { value: 'github' }
    });
    fireEvent.change(screen.getByLabelText('リポジトリURL'), {
      target: { value: 'https://github.com/test/repo.git' }
    });
    fireEvent.change(screen.getByLabelText('表示名'), {
      target: { value: 'テストリポジトリ' }
    });
    fireEvent.click(screen.getByText('登録'));

    // Assert
    await waitFor(() => {
      expect(screen.getByText('登録が完了しました')).toBeInTheDocument();
    });
    expect(モックAPIクライアント.リポジトリを登録).toHaveBeenCalledWith({
      プロバイダー: 'github',
      リモートURL: 'https://github.com/test/repo.git',
      表示名: 'テストリポジトリ'
    });
  });

  test('必須項目未入力時にエラーメッセージが表示される', () => {
    // Arrange
    render(<リポジトリ登録フォーム />);

    // Act
    fireEvent.click(screen.getByText('登録'));

    // Assert
    expect(screen.getByText('プロバイダーを選択してください')).toBeInTheDocument();
    expect(screen.getByText('リポジトリURLを入力してください')).toBeInTheDocument();
  });
});
```

### 統合テスト

#### API統合テスト
```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

class TestリポジトリAPI統合:
    """リポジトリAPI統合テスト"""
    
    def setup_method(self):
        self.クライアント = TestClient(app)
    
    def test_リポジトリ登録から検索まで_統合シナリオ(self):
        """リポジトリ登録から検索までの統合シナリオをテスト"""
        
        # 1. リポジトリ登録
        登録データ = {
            "プロバイダー": "github",
            "リモートURL": "https://github.com/test/repo.git",
            "表示名": "統合テスト用リポジトリ"
        }
        
        登録レスポンス = self.クライアント.post("/repos", json=登録データ)
        assert 登録レスポンス.status_code == 201
        
        リポジトリID = 登録レスポンス.json()["リポジトリID"]
        
        # 2. 解析実行
        解析レスポンス = self.クライアント.post(f"/repos/{リポジトリID}/parse", json={"種別": "FULL"})
        assert 解析レスポンス.status_code == 202
        
        # 3. 解析完了まで待機（実際の実装では非同期処理）
        # ここではモックまたはテスト用の同期処理を使用
        
        # 4. Wiki取得
        Wikiレスポンス = self.クライアント.get(f"/repos/{リポジトリID}/wiki")
        assert Wikiレスポンス.status_code == 200
        assert "目次" in Wikiレスポンス.json()
        
        # 5. 検索実行
        検索レスポンス = self.クライアント.get("/search", params={"q": "テスト", "repo_ids": [リポジトリID]})
        assert 検索レスポンス.status_code == 200
        assert len(検索レスポンス.json()["結果"]) > 0
```

### E2Eテスト

#### Playwright使用例
```typescript
import { test, expect } from '@playwright/test';

test.describe('DeepWiki-OMR E2Eテスト', () => {
  test('リポジトリ登録からWiki閲覧まで', async ({ page }) => {
    // 1. アプリケーションにアクセス
    await page.goto('/');
    
    // 2. リポジトリ登録画面に移動
    await page.click('text=新しいリポジトリを追加');
    
    // 3. リポジトリ情報を入力
    await page.selectOption('[data-testid=プロバイダー選択]', 'github');
    await page.fill('[data-testid=リポジトリURL]', 'https://github.com/test/sample-repo.git');
    await page.fill('[data-testid=表示名]', 'サンプルリポジトリ');
    
    // 4. 登録実行
    await page.click('text=登録');
    
    // 5. 登録完了を確認
    await expect(page.locator('text=登録が完了しました')).toBeVisible();
    
    // 6. 解析開始
    await page.click('text=解析開始');
    
    // 7. 解析完了まで待機
    await expect(page.locator('text=解析完了')).toBeVisible({ timeout: 60000 });
    
    // 8. Wiki表示
    await page.click('text=Wikiを表示');
    
    // 9. Wiki内容を確認
    await expect(page.locator('[data-testid=wiki目次]')).toBeVisible();
    await expect(page.locator('[data-testid=wikiコンテンツ]')).toContainText('README');
    
    // 10. 検索機能をテスト
    await page.fill('[data-testid=検索ボックス]', 'function');
    await page.click('[data-testid=検索実行]');
    
    // 11. 検索結果を確認
    await expect(page.locator('[data-testid=検索結果]')).toBeVisible();
    await expect(page.locator('[data-testid=検索結果] >> text=function')).toBeVisible();
  });
  
  test('RAG検索機能', async ({ page }) => {
    // 前提: リポジトリが既に登録・解析済み
    await page.goto('/');
    
    // 1. RAG検索タブに切り替え
    await page.click('text=RAG検索');
    
    // 2. 質問を入力
    await page.fill('[data-testid=RAG質問入力]', 'このコードの主な機能は何ですか？');
    
    // 3. 検索実行
    await page.click('[data-testid=RAG検索実行]');
    
    // 4. 回答を確認
    await expect(page.locator('[data-testid=RAG回答]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid=RAG引用]')).toHaveCount.greaterThanOrEqual(3);
  });
});
```

## テストデータ管理

### テストデータ戦略
```yaml
テストデータ種別:
  - 固定データ: 予測可能な結果が必要なテスト用
  - ランダムデータ: 境界値テスト用
  - 実データサンプル: 本番環境に近い条件でのテスト用

データ管理:
  - テストデータベース: 各テスト実行前にリセット
  - モックデータ: 外部API呼び出しのモック
  - ファクトリーパターン: テストデータ生成の標準化
```

### テストデータファクトリー例
```python
import factory
from datetime import datetime
from api.モデル.リポジトリ import リポジトリ

class リポジトリファクトリー(factory.Factory):
    """テスト用リポジトリデータファクトリー"""
    
    class Meta:
        model = リポジトリ
    
    リポジトリID = factory.Sequence(lambda n: f"repo-{n:04d}")
    プロバイダー = "github"
    リモートURL = factory.LazyAttribute(lambda obj: f"https://github.com/test/{obj.リポジトリID}.git")
    表示名 = factory.Faker('company', locale='ja_JP')
    デフォルトブランチ = "main"
    ステータス = "READY"
    最終スキャンSHA = factory.Faker('sha1')
    最終スキャン日時 = factory.LazyFunction(datetime.now)

# 使用例
def test_リポジトリ一覧取得():
    # テストデータ作成
    リポジトリ1 = リポジトリファクトリー.create()
    リポジトリ2 = リポジトリファクトリー.create(プロバイダー="codecommit")
    
    # テスト実行
    結果 = リポジトリサービス.一覧を取得()
    
    # 検証
    assert len(結果) == 2
    assert リポジトリ1.リポジトリID in [r.リポジトリID for r in 結果]
```

## パフォーマンステスト

### 負荷テスト設定
```yaml
ツール: Locust

シナリオ:
  - 通常検索: 100 req/s, 5分間
  - RAG検索: 10 req/s, 5分間
  - リポジトリ登録: 1 req/s, 10分間
  - Wiki表示: 50 req/s, 5分間

成功基準:
  - 応答時間 p95 < 目標値
  - エラー率 < 1%
  - スループット > 目標値
```

### Locustテストスクリプト例
```python
from locust import HttpUser, task, between

class DeepWikiOMRユーザー(HttpUser):
    """DeepWiki-OMRの負荷テストユーザー"""
    
    wait_time = between(1, 3)  # 1-3秒の間隔でリクエスト
    
    def on_start(self):
        """テスト開始時の初期化"""
        # 認証トークン取得など
        pass
    
    @task(3)
    def 通常検索(self):
        """通常検索の負荷テスト"""
        検索クエリ = "function"
        self.client.get(f"/search?q={検索クエリ}", name="通常検索")
    
    @task(1)
    def RAG検索(self):
        """RAG検索の負荷テスト"""
        質問 = "このコードの機能を教えて"
        self.client.post("/search/rag", json={"質問": 質問}, name="RAG検索")
    
    @task(2)
    def Wiki表示(self):
        """Wiki表示の負荷テスト"""
        リポジトリID = "repo-0001"  # テスト用固定ID
        self.client.get(f"/repos/{リポジトリID}/wiki", name="Wiki表示")
```

## テスト自動化

### CI/CDパイプライン統合
```yaml
GitHub Actions設定:
  
  単体テスト:
    - トリガー: プッシュ、プルリクエスト
    - 実行環境: Ubuntu latest
    - Python 3.11, Node.js 18
    - カバレッジレポート生成
  
  統合テスト:
    - トリガー: プルリクエスト
    - 実行環境: Docker Compose
    - テスト用データベース起動
    - 外部サービスモック
  
  E2Eテスト:
    - トリガー: main ブランチマージ
    - 実行環境: ステージング環境
    - Playwright実行
    - スクリーンショット保存
```

### テスト結果レポート
```yaml
カバレッジレポート:
  - ツール: pytest-cov, jest
  - 形式: HTML, XML
  - 閾値: 80%未満で失敗

テスト結果通知:
  - Slack通知: 失敗時
  - GitHub PR コメント: カバレッジ情報
  - メール通知: 重要な失敗時
```

## 品質ゲート

### リリース前チェックリスト
```yaml
必須項目:
  ✓ 単体テスト 100% パス
  ✓ 統合テスト 100% パス
  ✓ E2Eテスト 100% パス
  ✓ コードカバレッジ > 80%
  ✓ セキュリティスキャン パス
  ✓ パフォーマンステスト パス
  ✓ コードレビュー完了

推奨項目:
  ✓ 負荷テスト実行
  ✓ 脆弱性スキャン
  ✓ アクセシビリティテスト
  ✓ ブラウザ互換性テスト
```

### 品質メトリクス
```yaml
追跡指標:
  - テスト実行時間
  - テスト成功率
  - バグ検出率
  - 修正時間
  - カバレッジ推移

目標値:
  - テスト実行時間: < 10分
  - テスト成功率: > 99%
  - バグ検出率: > 90%
  - 修正時間: < 24時間
```