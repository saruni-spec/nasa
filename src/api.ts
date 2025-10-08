// All API communications

import {
  SearchResult,
  KnowledgeGraphData,
  AnalyticsData,
  ResearchCluster,
  ConceptRelationship,
} from "./types";

export class APIService {
  private baseUrl: string;

  constructor(baseUrl: string = "") {
    this.baseUrl = baseUrl;
  }

  /**
   * Search for publications
   */
  async search(query: string, limit: number = 20): Promise<SearchResult[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/search?q=${encodeURIComponent(
          query
        )}&limit=${limit}`
      );

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Search error:", error);
      throw error;
    }
  }

  /**
   * Send message to chatbot
   */
  async sendChatMessage(message: string): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chatbot`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error(`Chatbot request failed: ${response.statusText}`);
      }

      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error("Chatbot error:", error);
      throw error;
    }
  }

  /**
   * Get knowledge graph data
   */
  async getKnowledgeGraph(limit: number = 50): Promise<KnowledgeGraphData> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/knowledge-graph?limit=${limit}`
      );

      if (!response.ok) {
        throw new Error(
          `Knowledge graph request failed: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("Knowledge graph error:", error);
      throw error;
    }
  }

  /**
   * Get analytics data
   */
  async getAnalytics(): Promise<AnalyticsData> {
    try {
      const response = await fetch(`${this.baseUrl}/api/analytics`);

      if (!response.ok) {
        throw new Error(`Analytics request failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Analytics error:", error);
      throw error;
    }
  }

  /**
   * Get research clusters
   */
  async getClusters(): Promise<ResearchCluster[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/knowledge-graph/clusters`
      );

      if (!response.ok) {
        throw new Error(`Clusters request failed: ${response.statusText}`);
      }

      const data = await response.json();
      return data.clusters;
    } catch (error) {
      console.error("Clusters error:", error);
      throw error;
    }
  }

  /**
   * Get concept relationships
   */
  async getRelationships(): Promise<ConceptRelationship[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/knowledge-graph/relationships`
      );

      if (!response.ok) {
        throw new Error(`Relationships request failed: ${response.statusText}`);
      }

      const data = await response.json();
      return data.relationships;
    } catch (error) {
      console.error("Relationships error:", error);
      throw error;
    }
  }
}
