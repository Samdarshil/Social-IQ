export type PlatformId = 'youtube' | 'instagram' | 'x' | 'linkedin'
export const PLATFORM_IDS: PlatformId[] = ['youtube', 'instagram', 'x', 'linkedin']
export const PLATFORM_LABEL: Record<PlatformId, string> = { youtube: 'YouTube', instagram: 'Instagram', x: 'X', linkedin: 'LinkedIn' }
export const CATEGORIES = ['Tutorials', 'Behind the Scenes', 'Opinions', 'Case Studies', 'News & Trends', 'Q&A'] as const
export const CONTENT_TYPES: Record<PlatformId, string[]> = {
  youtube: ['video', 'short'], instagram: ['reel', 'carousel', 'image'], x: ['post', 'thread'], linkedin: ['post', 'article', 'carousel'],
}

export interface AuthUser { id: number; email: string | null; display_name: string; is_demo: boolean }
export interface DataSource { mode: 'demo' | 'live' | 'empty'; label: string; platforms_live: string[]; platforms_demo: string[] }
export interface SourceInfo { source: DataSource; creator: string; posts: number; notes: string[] }

export interface Agg { posts: number; views: number; interactions: number; likes: number; comments: number; shares: number; engagement_rate: number | null; avg_views: number | null }
export interface Summary {
  window_days: number; source: DataSource; current: Agg; previous: Agg
  deltas: { views_pct: number | null; interactions_pct: number | null; engagement_rate_pct: number | null; posts_pct: number | null }
  followers: { total: number; available: boolean; start: number | null; end: number | null; change: number | null; pct: number | null }
  platforms_included: PlatformId[]; as_of: string | null
}
export interface SeriesPoint { date: string; views: number; interactions: number; posts: number; engagement_rate: number | null }
export interface Timeseries { freq: string; points: SeriesPoint[]; by_platform: (SeriesPoint & { platform: PlatformId })[]; followers: { date: string; followers: number }[] }

export interface PlatformRow {
  platform: PlatformId; label: string; posts: number; views: number; interactions: number; engagement_rate: number | null; avg_views: number | null
  followers: number | null; follower_growth_pct: number | null; views_per_follower: number | null; interactions_per_1k_followers: number | null
  median_engagement_rate: number; avg_perf_index: number
}
export interface PlatformComparison { platforms: PlatformRow[]; best: Record<string, PlatformId | null>; note: string; focus?: PlatformId | null }

export interface ContentItem {
  platform: PlatformId; content_id: string; title: string; content_type: string; category: string; published_at: string
  views: number; likes: number; comments: number; shares: number; engagement_rate: number; perf_index: number
}
export interface ContentList { total: number; items: ContentItem[] }
export interface TopContent { items: ContentItem[]; worst: boolean; note?: string }
export interface ContentDetail extends ContentItem {
  duration_sec: number | null; publish_slot: string
  vs_platform_median: { views_ratio: number; engagement_rate_ratio: number }
}

export interface InsightCard { kind: string; tone: 'positive' | 'negative' | 'neutral' | 'attention'; headline: string; why: string; evidence: Record<string, unknown> }
export interface Insights { cards: InsightCard[]; source: DataSource }

export interface Driver { dimension: string; key: string; effect: number; rate_effect: number; mix_effect: number; rate_now: number | null; rate_before: number | null; posts_now: number; posts_before: number }
export interface EngagementChange {
  available: boolean; reason?: string; days: number; rate_now: number; rate_before: number; change_pct: number | null; significant: boolean; p_value: number | null
  comment_share_now: number; comment_share_before: number; by_platform: Driver[]; by_category: Driver[]
  top_negative: Driver[]; top_positive: Driver[]; posts_now: number; posts_before: number; method: string
}

export interface HeatCell { day: string; dow: number; block: number; score: number; n: number }
export interface BestTimes {
  by_platform: Record<string, {
    best_hours: { hour: number; score: number; n: number }[]; best_days: { day: string; score: number; n: number }[]
    heatmap: HeatCell[]; baseline: number; posts: number
  }>
  timezone: string; note: string
}
export interface CategoryRow { category: string; platform?: PlatformId; content_type?: string; posts: number; avg_views: number; engagement_rate: number; perf_index: number }
export interface Categories { categories: CategoryRow[]; by_platform: CategoryRow[]; formats: CategoryRow[] }
export interface Breakdown { platforms: { platform: PlatformId; label: string; likes: number; comments: number; shares: number; likes_pct: number; comments_pct: number; shares_pct: number }[] }

export interface AnomalyItem { platform: PlatformId; metric: string; direction: 'high' | 'low'; z: number; content_id: string | null; title: string | null; published_at: string; value: number; typical: number; message: string }
export interface Anomalies { items: AnomalyItem[]; count: number; threshold: number; window_days: number; method: string }
export interface CrossPlatform {
  category_fit: { category: string; platform: PlatformId; n: number; perf: number; er: number; lift: number }[]
  best_platform_by_category: Record<string, PlatformId>
  same_idea: { posts: { platform: PlatformId; title: string; views: number; engagement_rate: number; views_per_follower: number | null }[]; best_platform: PlatformId }[]
  focus: PlatformId | null; method_note: string
}
export interface Profile {
  available: boolean; reason?: string
  dimensions: Record<string, { score: number; value: number; unit: string; formula: string }>
  strengths: string[]; focus_area: string; posts_analyzed: number; summary: string; note: string
}

export interface Factor { group: string; impact: number; text: string }
export interface Recommendation { kind: string; text: string; delta: number; change: Partial<{ publish_at: string; category: string; title: string; content_type: string }> }
export interface Prediction {
  score: number; label: 'LOW' | 'MEDIUM' | 'HIGH'; model: string
  interval: { low: number; high: number; level: number; half_width: number; empirical_test_coverage: number }
  explanation?: { base_score: number; positive: Factor[]; negative: Factor[]; method: string }
  recommendations?: Recommendation[]
  spec: PredictSpec
}
export interface PredictSpec { title: string; platform: PlatformId; category: string; content_type: string; duration_sec: number | null; publish_at: string }
export interface ModelCard {
  selected_model: string; xgboost_available: boolean; target: string; classes: string; n_posts: number; n_dev: number; n_test: number; split: string
  candidates: { name: string; cv_mae: number; cv_mae_std: number; cv_r2: number; selected: boolean }[]
  test: { mae: number; rmse: number; r2: number; spearman: number; bias: number; top_third_hit_rate: number | null; baseline_mae: number; mae_improvement_pct: number }
  interval: { level: number; half_width: number; empirical_test_coverage: number; method: string }
  global_importance: { group: string; importance: number }[]
  trained_at: string; data_mode: string; leakage_controls: string[]; caveats: string[]
}
export interface Idea { platform: PlatformId; category: string; content_type: string; hour: number; day: string; score: number }

// Assistant
export type AssistantCard = { type: string } & Record<string, unknown>
export interface ChatResponse {
  answer: string; cards: AssistantCard[]; tool_calls: { name: string; args: Record<string, unknown>; ok: boolean }[]
  mode: 'llm' | 'local'; mode_label: string; notice?: string | null; source: DataSource
}

// Platforms / privacy
export interface PlatformConn {
  platform: PlatformId; label: string; configured: boolean; scopes: string[]; notes: string
  status: 'demo' | 'connected' | 'available' | 'not_configured'; account_label: string | null; last_synced_at: string | null; connected_at: string | null
}
export interface PrivacyOverview {
  is_demo: boolean; stored_content_rows: number
  connections: { platform: PlatformId; account_label: string; scopes: string[]; connected_at: string; last_synced_at: string | null; access: string }[]
  permissions: Record<string, { label: string; scopes: string[]; notes: string }>
  stores: string[]; never_stores: string[]
  ai: { provider_configured: boolean; model: string | null; sends: string[]; never_sends: string[]; note: string }
  security: { oauth_only: boolean; read_only_scopes: boolean; token_encryption: string; password_hashing: string; transport: string; not_claimed: string[] }
}

// YouTube trending engagement clusters (Kaggle dataset)
export interface TrendCluster {
  id: number; label: string; size: number; share: number; descriptor: string
  centroid_z: Record<string, number>
  medians: { views: number; likes: number; comments: number; engagement_rate: number; like_rate: number; comment_rate: number }
  traits: { dislike_share: number | null; days_to_trend: number | null; title_length: number | null; tag_count: number | null }
  top_categories: { name: string; share: number; lift: number }[]
  example: { title: string; channel: string; views: number; engagement_rate: number }[]
}
export interface TrendCategory {
  name: string; n: number; median_views: number; median_likes: number; median_comments: number; median_engagement_rate: number
  median_like_rate: number; median_comment_rate: number; share_higher_cluster: number; share_lower_cluster: number
}
export interface TrendResult {
  country: string; country_name: string; source: { kind: 'raw_csv' | 'snapshot'; note?: string; file?: string }
  dataset: { rows_raw: number; videos_unique: number; videos_used: number; excluded: Record<string, number>; trending_window: { first: string | null; last: string | null } }
  features_definition: string
  correlations: { labels: string[]; spearman: number[][]; note: string }
  category: { rows: TrendCategory[]; overall_median_engagement_rate: number; min_n_for_test: number; kruskal: { h: number; p: number; epsilon_sq: number; categories: number; videos: number } | null }
  model: { algorithm: string; k: number; features: string[]; scaling: string; silhouette_by_k: Record<string, number>; silhouette: number; silhouette_reading: string; best_silhouette_k: number
    k_choice: string; gmm_agreement_ari: number; stability_ari_mean: number; stability_ari_min: number; pca_note: string; tiers_consistent: boolean }
  clusters: TrendCluster[]
  scatter: { explained_variance: number[]; axes: Record<string, number>[]; points: [number, number, number][] }
  takeaways: string[]; caveats: string[]
}
export interface TrendCountry { country: string; name: string; videos?: number; silhouette?: number; stability_ari?: number; median_engagement_rate?: number }
