export interface Metrics {
  total_publications: number;
  recent_publications: number;
  nasa_related_count: number;
  nasa_related_percent: number;
  total_authors: number;
  unique_topics: number;
}

export interface Publication {
  article_id: number;
  pmcid: string;
  title: string;
  section: string;
  snippet: string;
  relevance_score: number;
  journal?: string;
  publication_date?: string;
  keywords?: string[];
}

export interface SearchResult extends Publication {
  // Additional search-specific fields if needed
}

export interface SavedArticle {
  id: number;
  pmcid: string;
  title: string;
  snippet: string;
  link: string;
  journal?: string;
  date?: string;
}

export interface ChatMessage {
  text: string;
  sender: "user" | "bot";
  timestamp: number;
}

export interface Insight {
  icon: string;
  title: string;
  content: string;
}

export interface ChartData {
  labels: string[];
  data: number[];
}

export interface TrendsData {
  labels: string[];
  publications: number[];
  citations?: number[];
}

export interface AnalyticsData {
  trends: TrendsData;
  impact?: ChartData;
  researchAreas?: ChartData;
  methodology?: ChartData;
  topCited?: ChartData;
  topFunders?: ChartData;
  topicsDistribution?: ChartData;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  size?: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  weight?: number;
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ResearchCluster {
  name: string;
  description?: string;
  keywords?: string;
  count?: number;
}

export interface ConceptRelationship {
  source?: string;
  target?: string;
  concept1?: string;
  concept2?: string;
  strength?: number;
}

export interface ServerData {
  metrics: Metrics;
  researchAreas: any;
  knowledgeGaps: any;
  insights: Insight[];
  analytics: AnalyticsData;
}

export interface ToastOptions {
  message: string;
  type: "success" | "error" | "warning" | "info";
  duration?: number;
}

export type TabId =
  | "dashboard"
  | "explore"
  | "knowledge-graph"
  | "analytics"
  | "saved-articles";
