// Dashboard management

import { ChartService } from "./chart";
import { ToastService } from "./toast";
import { APIService } from "./api";
import { Metrics, Insight, AnalyticsData } from "./types";

export class DashboardController {
  private chartService: ChartService;
  private toastService: ToastService;
  private apiService: APIService;
  private metrics: Metrics;
  private insights: Insight[];
  private analytics: AnalyticsData | null = null;

  constructor(
    chartService: ChartService,
    toastService: ToastService,
    apiService: APIService,
    metrics: Metrics,
    insights: Insight[],
    analytics?: AnalyticsData
  ) {
    this.chartService = chartService;
    this.toastService = toastService;
    this.apiService = apiService;
    this.metrics = metrics;
    this.insights = insights;
    this.analytics = analytics || null;
  }

  /**
   * Initialize dashboard
   */
  async initialize(): Promise<void> {
    try {
      this.renderMetrics();
      this.renderInsights();
      await this.renderCharts();
    } catch (error) {
      console.error("Dashboard initialization error:", error);
      this.toastService.error("Failed to initialize dashboard");
    }
  }

  /**
   * Render metrics cards
   */
  private renderMetrics(): void {
    // Metrics are already in the HTML from server-side rendering
    // This method could be used to update them dynamically if needed
    console.log("Dashboard metrics loaded:", this.metrics);
  }

  /**
   * Render insights
   */
  private renderInsights(): void {
    // Insights are already in the HTML from server-side rendering
    console.log("Dashboard insights loaded:", this.insights);
  }

  /**
   * Render all charts
   */
  async renderCharts(): Promise<void> {
    try {
      // If analytics data is not provided, fetch it
      if (!this.analytics) {
        this.analytics = await this.apiService.getAnalytics();
      }

      // Render trends chart
      if (this.analytics.trends) {
        this.chartService.createLineChart(
          "trends-chart",
          this.analytics.trends,
          "Publication Trends Over Time"
        );
      }

      // Render top funders chart
      if (this.analytics.topFunders) {
        this.chartService.createDoughnutChart(
          "dashboard-top-funders-chart",
          this.analytics.topFunders,
          "Top Funding Sources"
        );
      }

      // Render topics distribution chart
      if (this.analytics.topicsDistribution) {
        this.chartService.createBarChart(
          "dashboard-topics-chart",
          this.analytics.topicsDistribution,
          "Research Topics Distribution",
          { color: "#805ad5" }
        );
      }

      console.log("Dashboard charts rendered successfully");
    } catch (error) {
      console.error("Error rendering charts:", error);
      this.toastService.error("Failed to load dashboard charts");
    }
  }

  /**
   * Refresh dashboard data
   */
  async refresh(): Promise<void> {
    try {
      this.analytics = await this.apiService.getAnalytics();
      await this.renderCharts();
      this.toastService.success("Dashboard refreshed");
    } catch (error) {
      console.error("Error refreshing dashboard:", error);
      this.toastService.error("Failed to refresh dashboard");
    }
  }

  /**
   * Cleanup
   */
  destroy(): void {
    // Destroy charts when leaving dashboard
    this.chartService.destroyChart("trends-chart");
    this.chartService.destroyChart("dashboard-top-funders-chart");
    this.chartService.destroyChart("dashboard-topics-chart");
  }
}
