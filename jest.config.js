const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Next.js アプリのパスを指定
  dir: './',
})

// Jest の設定
const customJestConfig = {
  // セットアップファイル
  setupFilesAfterEnv: ['<rootDir>/test/setup.ts'],
  
  // テスト環境
  testEnvironment: 'jest-environment-jsdom',
  
  // モジュールパスマッピング
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  
  // テストファイルのパターン
  testMatch: [
    '<rootDir>/test/**/*.test.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.test.{js,jsx,ts,tsx}',
  ],
  
  // 無視するパターン
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/test/e2e/',
  ],
  
  // カバレッジ設定
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/index.{js,jsx,ts,tsx}',
  ],
  
  // カバレッジ閾値
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
  
  // カバレッジレポート
  coverageReporters: ['text', 'lcov', 'html'],
  
  // モック設定
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  
  // 変換設定
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }],
  },
  
  // 変換を無視するパターン
  transformIgnorePatterns: [
    '/node_modules/',
    '^.+\\.module\\.(css|sass|scss)$',
  ],
  
  // モジュールファイル拡張子
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
}

// Next.js の設定と統合
module.exports = createJestConfig(customJestConfig)