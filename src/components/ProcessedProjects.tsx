'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { FaTimes, FaTh, FaList, FaGithub, FaAws, FaPlus } from 'react-icons/fa';

// --- 型定義 ---
interface Repository {
  リポジトリID: string;
  表示名: string;
  プロバイダー: 'github' | 'codecommit';
  ステータス: 'READY' | 'PARSING' | 'FAILED';
  最終スキャン日時: string | null;
  更新日時: string;
}

interface NewRepoState {
    remoteUrl: string;
    displayName: string;
    provider: 'github' | 'codecommit';
}

interface ProcessedProjectsProps {
  showHeader?: boolean;
  maxItems?: number;
  className?: string;
  messages?: Record<string, Record<string, string>>; 
}

// --- コンポーネント ---
export default function ProcessedProjects({
  showHeader = true,
  maxItems,
  className = "",
  messages
}: ProcessedProjectsProps) {
  // --- State管理 ---
  const [projects, setProjects] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card');
  const [isAdding, setIsAdding] = useState(false);
  const [newRepo, setNewRepo] = useState<NewRepoState>({ remoteUrl: '', displayName: '', provider: 'github' });
  const [formError, setFormError] = useState<string | null>(null);

  // --- メッセージと翻訳 ---
  const defaultMessages = {
    title: 'Registered Repositories',
    searchPlaceholder: 'Search by name...',
    noProjects: 'No repositories found.',
    noSearchResults: 'No repositories match your search.',
    processedOn: 'Last updated:',
    loadingProjects: 'Loading repositories...',
    errorLoading: 'Error loading repositories:',
    backToHome: 'Back to Home',
    addRepo: 'Add Repository',
    cancel: 'Cancel',
    submit: 'Submit',
    repoUrl: 'Repository URL',
    displayName: 'Display Name',
    provider: 'Provider',
  };

  const t = (key: string) => {
    return messages?.projects?.[key] || defaultMessages[key as keyof typeof defaultMessages] || key;
  };

  // --- データ取得 ---
  const fetchProjects = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/repositories');
      if (!response.ok) throw new Error(`Failed to fetch projects: ${response.statusText}`);
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      setProjects(data.リポジトリ一覧 as Repository[]);
    } catch (e: unknown) {
      console.error("Failed to load projects from API:", e);
      setError(e instanceof Error ? e.message : "An unknown error occurred.");
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  // --- イベントハンドラ ---
  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setNewRepo(prev => ({ ...prev, [name]: value }));
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!newRepo.remoteUrl || !newRepo.displayName) {
      setFormError('URL and Display Name are required.');
      return;
    }

    try {
      const response = await fetch('/api/repositories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            リモートURL: newRepo.remoteUrl,
            表示名: newRepo.displayName,
            プロバイダー: newRepo.provider,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to add repository');
      }
      setIsAdding(false);
      setNewRepo({ remoteUrl: '', displayName: '', provider: 'github' });
      await fetchProjects(); // Refresh the list
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'An unknown error occurred');
    }
  };

  const handleDelete = async (repoId: string) => {
    if (!confirm(`Are you sure you want to delete this repository?`)) return;
    try {
      const response = await fetch(`/api/repositories/${repoId}`, { method: 'DELETE' });
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorBody.detail || response.statusText);
      }
      setProjects(prev => prev.filter(p => p.リポジトリID !== repoId));
    } catch (e: unknown) {
      console.error('Failed to delete project:', e);
      alert(`Failed to delete project: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  // --- フィルタリングとUIヘルパー ---
  const filteredProjects = useMemo(() => {
    const query = searchQuery.toLowerCase();
    return projects.filter(p => p.表示名.toLowerCase().includes(query));
  }, [projects, searchQuery]);

  const getStatusChip = (status: Repository['ステータス']) => {
    const base = "px-2 py-1 text-xs font-semibold rounded-full border";
    const colors = {
      READY: "bg-green-100 text-green-800 border-green-200",
      PARSING: "bg-blue-100 text-blue-800 border-blue-200",
      FAILED: "bg-red-100 text-red-800 border-red-200",
    };
    return <span className={`${base} ${colors[status] || 'bg-gray-100'}`}>{status}</span>;
  };

  const getProviderIcon = (provider: Repository['プロバイダー']) => {
    const icons = {
      github: <FaGithub className="h-5 w-5 text-gray-500" title="GitHub" />,
      codecommit: <FaAws className="h-5 w-5 text-yellow-500" title="AWS CodeCommit" />,
    };
    return icons[provider] || null;
  };

  // --- レンダリング ---
  return (
    <div className={`${className}`}>
      {showHeader && (
        <header className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-[var(--accent-primary)]">{t('title')}</h1>
          <Link href="/" className="text-[var(--accent-primary)] hover:underline">{t('backToHome')}</Link>
        </header>
      )}

      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder={t('searchPlaceholder')} className="input-japanese block w-full pl-4 pr-12 py-2.5 border border-[var(--border-color)] rounded-lg bg-[var(--background)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]" />
          {searchQuery && <button onClick={() => setSearchQuery('')} className="absolute inset-y-0 right-0 flex items-center pr-3 text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"><FaTimes className="h-4 w-4" /></button>}
        </div>
        <div className="flex items-center gap-2">
            <button onClick={() => setIsAdding(!isAdding)} className="flex items-center gap-2 px-4 py-2.5 bg-[var(--accent-primary)] text-white rounded-lg hover:bg-opacity-90 transition-colors">
                <FaPlus /> {isAdding ? t('cancel') : t('addRepo')}
            </button>
            <div className="flex items-center bg-[var(--background)] border border-[var(--border-color)] rounded-lg p-1">
                <button onClick={() => setViewMode('card')} className={`p-2 rounded transition-colors ${viewMode === 'card' ? 'bg-[var(--accent-primary)] text-white' : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)]'}`} title="Card View"><FaTh className="h-4 w-4" /></button>
                <button onClick={() => setViewMode('list')} className={`p-2 rounded transition-colors ${viewMode === 'list' ? 'bg-[var(--accent-primary)] text-white' : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)]'}`} title="List View"><FaList className="h-4 w-4" /></button>
            </div>
        </div>
      </div>

      {isAdding && (
        <div className="p-4 mb-6 border border-[var(--border-color)] rounded-lg bg-[var(--card-bg)]">
          <form onSubmit={handleAddSubmit} className="space-y-4">
            <h2 className="text-xl font-semibold">{t('addRepo')}</h2>
            <div>
              <label htmlFor="remoteUrl" className="block text-sm font-medium mb-1">{t('repoUrl')}</label>
              <input type="text" id="remoteUrl" name="remoteUrl" value={newRepo.remoteUrl} onChange={handleFormChange} required className="input-japanese w-full p-2 border border-[var(--border-color)] rounded-lg bg-[var(--background)]" />
            </div>
            <div>
              <label htmlFor="displayName" className="block text-sm font-medium mb-1">{t('displayName')}</label>
              <input type="text" id="displayName" name="displayName" value={newRepo.displayName} onChange={handleFormChange} required className="input-japanese w-full p-2 border border-[var(--border-color)] rounded-lg bg-[var(--background)]" />
            </div>
            <div>
              <label htmlFor="provider" className="block text-sm font-medium mb-1">{t('provider')}</label>
              <select id="provider" name="provider" value={newRepo.provider} onChange={handleFormChange} className="w-full p-2 border border-[var(--border-color)] rounded-lg bg-[var(--background)]">
                <option value="github">GitHub</option>
                <option value="codecommit">AWS CodeCommit</option>
              </select>
            </div>
            {formError && <p className="text-sm text-red-500">{formError}</p>}
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setIsAdding(false)} className="px-4 py-2 rounded-lg bg-gray-200 text-gray-800 hover:bg-gray-300">{t('cancel')}</button>
              <button type="submit" className="px-4 py-2 rounded-lg bg-[var(--accent-primary)] text-white hover:bg-opacity-90">{t('submit')}</button>
            </div>
          </form>
        </div>
      )}

      {isLoading && <p className="text-[var(--muted)]">{t('loadingProjects')}</p>}
      {error && <p className="text-[var(--highlight)]">{t('errorLoading')} {error}</p>}

      {!isLoading && !error && (
        filteredProjects.length > 0 ? (
          <div className={viewMode === 'card' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-2'}>
            {filteredProjects.map((project) => (
              <div key={project.リポジトリID} className="relative p-4 border border-[var(--border-color)] rounded-lg bg-[var(--card-bg)] shadow-sm hover:shadow-md transition-all duration-200">
                <div className="flex justify-between items-start">
                  <Link href={`/wiki/projects/${project.リポジトリID}`} className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-[var(--link-color)] hover:underline mb-2 truncate" title={project.表示名}>{project.表示名}</h3>
                  </Link>
                  <button type="button" onClick={() => handleDelete(project.リポジトリID)} className="ml-2 text-[var(--muted)] hover:text-[var(--foreground)]" title="Delete project"><FaTimes className="h-4 w-4" /></button>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-2">
                    {getProviderIcon(project.プロバイダー)}
                    {getStatusChip(project.ステータス)}
                  </div>
                  <p className="text-xs text-[var(--muted)]">{t('processedOn')} {new Date(project.更新日時).toLocaleDateString()}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[var(--muted)]">{searchQuery ? t('noSearchResults') : t('noProjects')}</p>
        )
      )}
    </div>
  );
}
