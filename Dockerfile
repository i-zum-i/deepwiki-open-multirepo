# 本番用マルチステージDockerfile

# ベースイメージ
FROM python:3.11-slim as python-base

# 環境変数の設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 作業ディレクトリの設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python依存関係のインストール
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 非rootユーザーの作成
RUN groupadd -r appuser && useradd -r -g appuser appuser

# API サーバー用ステージ
FROM python-base as api

# APIコードのコピー
COPY api/ /app/api/
COPY docs/ /app/docs/

# ファイルの所有権を変更
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ポート8000を公開
EXPOSE 8000

# 本番用の起動コマンド
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ワーカー用ステージ
FROM python-base as worker

# APIコードのコピー（ワーカーもAPIコードを使用）
COPY api/ /app/api/
COPY docs/ /app/docs/

# ファイルの所有権を変更
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# ワーカー用の起動コマンド
CMD ["python", "-m", "api.worker"]

# フロントエンド用ステージ
FROM node:18-alpine as frontend-deps

WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# 依存関係のインストール
RUN npm ci --only=production && npm cache clean --force

# フロントエンドビルドステージ
FROM node:18-alpine as frontend-builder

WORKDIR /app

# 依存関係をコピー
COPY --from=frontend-deps /app/node_modules ./node_modules
COPY package*.json ./

# ソースコードのコピー
COPY src/ ./src/
COPY public/ ./public/
COPY next.config.ts ./
COPY tailwind.config.js ./
COPY tsconfig.json ./
COPY postcss.config.mjs ./

# アプリケーションのビルド
RUN npm run build

# フロントエンド本番用ステージ
FROM node:18-alpine as frontend

WORKDIR /app

# 非rootユーザーの作成
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# 必要なファイルのコピー
COPY --from=frontend-builder /app/public ./public
COPY --from=frontend-builder /app/package.json ./package.json

# ビルド成果物のコピー
COPY --from=frontend-builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=frontend-builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 非rootユーザーに切り替え
USER nextjs

# ポート3000を公開
EXPOSE 3000

# 環境変数の設定
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# 本番サーバーの起動
CMD ["node", "server.js"]