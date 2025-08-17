'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { FaGithub, FaAws, FaSpinner, FaExclamationCircle, FaCheckCircle } from 'react-icons/fa';

// --- 型定義 ---
interface RepositoryDetails {
  リポジトリID: string;
  表示名: string;
  プロバイダー: 'github' | 'codecommit';
  リモートURL: string;
  ステータス: 'READY' | 'PARSING' | 'FAILED';
  最終スキャン日時: string | null;
  作成日時: string;
  更新日時: string;
  ページ数: number;
  最新ジョブ: any | null; // TODO: ジョブの型を定義
}

// --- コンポーネント ---
export default function RepositoryDetailPage() {
  // --- State管理 ---
  const params = useParams();
  const repoId = params.repo_id as string;
  const [repository, setRepository] = useState<RepositoryDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- データ取得 ---
  useEffect(() => {
    if (!repoId) return;

    const fetchRepositoryDetails = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/repositories/${repoId}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Failed to fetch repository details`);
        }
        const data = await response.json();
        setRepository(data as RepositoryDetails);
      } catch (e: unknown) {
        console.error("Failed to load repository details:", e);
        setError(e instanceof Error ? e.message : "An unknown error occurred.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchRepositoryDetails();
  }, [repoId]);

  // --- UIヘルパー ---
  const getStatusIcon = (status: RepositoryDetails['ステータス']) => {
    const iconProps = { className: "mr-2" };
    switch (status) {
      case 'READY':
        return <FaCheckCircle {...iconProps} className="text-green-500" />;
      case 'PARSING':
        return <FaSpinner {...iconProps} className="animate-spin text-blue-500" />;
      case 'FAILED':
        return <FaExclamationCircle {...iconProps} className="text-red-500" />;
      default:
        return null;
    }
  };

  const getProviderIcon = (provider: RepositoryDetails['プロバイダー']) => {
      return provider === 'github' 
        ? <FaGithub className="h-6 w-6 text-gray-700" /> 
        : <FaAws className="h-6 w-6 text-yellow-600" />;
  }

  // --- レンダリング ---
  if (isLoading) {
    return <div className="container mx-auto p-4 text-center">Loading...</div>;
  }

  if (error) {
    return <div className="container mx-auto p-4 text-center text-red-500">Error: {error}</div>;
  }

  if (!repository) {
    return <div className="container mx-auto p-4 text-center">Repository not found.</div>;
  }

  return (
    <div className="container mx-auto p-4">
      {/* ヘッダー */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
            {getProviderIcon(repository.プロバイダー)}
            <h1 className="text-3xl font-bold">{repository.表示名}</h1>
        </div>
        <Link href="/wiki/projects" className="text-blue-500 hover:underline">
          &larr; Back to Projects
        </Link>
      </div>

      {/* 詳細パネル */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 左カラム */}
          <div className="md:col-span-2 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-500">Repository URL</h3>
              <a href={repository.リモートURL} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
                {repository.リモートURL}
              </a>
            </div>
            <div>
              <h3 className="font-semibold text-gray-500">Status</h3>
              <div className="flex items-center">
                {getStatusIcon(repository.ステータス)}
                <span>{repository.ステータス}</span>
              </div>
            </div>
            <div>
              <h3 className="font-semibold text-gray-500">Last Scan</h3>
              <p>{repository.最終スキャン日時 ? new Date(repository.最終スキャン日時).toLocaleString() : 'N/A'}</p>
            </div>
          </div>

          {/* 右カラム */}
          <div className="space-y-4">
             <div>
                <h3 className="font-semibold text-gray-500">Repository ID</h3>
                <p className="text-sm text-gray-600 font-mono">{repository.リポジトリID}</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-500">Created</h3>
              <p>{new Date(repository.作成日時).toLocaleString()}</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-500">Last Updated</h3>
              <p>{new Date(repository.更新日時).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* アクションボタン */}
        <div className="mt-6 pt-6 border-t">
            <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
                Start Full Analysis
            </button>
        </div>
      </div>

      {/* TODO: ジョブ履歴などを表示するセクション */}
    </div>
  );
}
