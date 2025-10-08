// Application entry point
import { APIService } from "./api.js";
import { StorageService } from "./storage.js";
import { ChartService } from "./chart.js";
import { ToastService } from "./toast.js";
import { DashboardController } from "./dashboard.js";
import { SearchController } from "./search.js";
import { ChatbotController } from "./chatbot.js";
import { KnowledgeGraphController } from "./knowledgegraph.js";
import { SavedArticlesController } from "./save_articles.js";
import { NavigationController } from "./navigation.js";
import { ServerData } from "./types.js";

/**
 * Main Application Class
 */
class NASASpaceHubApp {
  private apiService: APIService;
  private storageService: StorageService;
  private chartService: ChartService;
  private toastService: ToastService;
  private dashboardController: DashboardController;
  private searchController: SearchController;
  private chatbotController: ChatbotController;
  private knowledgeGraphController: KnowledgeGraphController;
  private savedArticlesController: SavedArticlesController;
  private navigationController: NavigationController;

  constructor(serverData: ServerData) {
    // Initialize services
    this.apiService = new APIService();
    this.storageService = new StorageService();
    this.chartService = new ChartService();
    this.toastService = new ToastService();

    // Initialize controllers with dependency injection
    this.dashboardController = new DashboardController(
      this.chartService,
      this.toastService,
      this.apiService,
      serverData.metrics,
      serverData.insights,
      serverData.analytics
    );

    this.searchController = new SearchController(
      this.apiService,
      this.storageService,
      this.toastService
    );

    this.chatbotController = new ChatbotController(
      this.apiService,
      this.storageService,
      this.toastService
    );

    this.knowledgeGraphController = new KnowledgeGraphController(
      this.apiService,
      this.toastService
    );

    this.savedArticlesController = new SavedArticlesController(
      this.storageService,
      this.toastService
    );

    this.navigationController = new NavigationController(
      this.dashboardController,
      this.searchController,
      this.chatbotController,
      this.knowledgeGraphController,
      this.savedArticlesController
    );
  }

  /**
   * Initialize the application
   */
  async initialize(): Promise<void> {
    try {
      console.log("Initializing NASA Space Hub...");

      // Initialize chatbot (always available)
      this.chatbotController.initialize();

      // Initialize navigation (handles tab switching and lazy loading)
      this.navigationController.initialize();

      // Initialize dashboard (default tab)
      await this.dashboardController.initialize();

      // Setup global error handler
      this.setupErrorHandler();

      // Setup knowledge graph button
      this.setupKnowledgeGraphButton();

      console.log("NASA Space Hub initialized successfully");
      this.toastService.success("Welcome to NASA Space Hub!", 2000);
    } catch (error) {
      console.error("Application initialization error:", error);
      this.toastService.error("Failed to initialize application");
    }
  }

  /**
   * Setup global error handler
   */
  private setupErrorHandler(): void {
    window.addEventListener("error", (event) => {
      console.error("Global error:", event.error);
      this.toastService.error("An unexpected error occurred");
    });

    window.addEventListener("unhandledrejection", (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      this.toastService.error("An unexpected error occurred");
    });
  }

  /**
   * Setup knowledge graph button
   */
  private setupKnowledgeGraphButton(): void {
    // Make loadKnowledgeGraph available globally for the button
    (window as any).loadKnowledgeGraph = async () => {
      await this.knowledgeGraphController.loadGraph();
    };
  }

  /**
   * Get a controller instance (for debugging/testing)
   */
  getController(name: string): any {
    const controllers: { [key: string]: any } = {
      dashboard: this.dashboardController,
      search: this.searchController,
      chatbot: this.chatbotController,
      knowledgeGraph: this.knowledgeGraphController,
      savedArticles: this.savedArticlesController,
      navigation: this.navigationController,
    };
    return controllers[name];
  }

  /**
   * Cleanup and destroy
   */
  destroy(): void {
    this.dashboardController.destroy();
    this.searchController.destroy();
    this.chatbotController.destroy();
    this.knowledgeGraphController.destroy();
    this.savedArticlesController.destroy();
    this.chartService.destroyAllCharts();
    this.toastService.clearAll();
    console.log("Application destroyed");
  }
}

/**
 * Initialize application when DOM is ready
 */
document.addEventListener("DOMContentLoaded", () => {
  // Get server data from embedded script
  const serverDataElement = document.getElementById("server-data");
  let serverData: ServerData;

  if (serverDataElement) {
    try {
      serverData = JSON.parse(serverDataElement.textContent || "{}");
    } catch (error) {
      console.error("Failed to parse server data:", error);
      serverData = {
        metrics: {
          total_publications: 0,
          recent_publications: 0,
          nasa_related_count: 0,
          nasa_related_percent: 0,
          total_authors: 0,
          unique_topics: 0,
        },
        researchAreas: {},
        knowledgeGaps: {},
        insights: [],
        analytics: {
          trends: { labels: [], publications: [] },
        },
      };
    }
  } else {
    console.warn("Server data element not found, using defaults");
    serverData = {
      metrics: {
        total_publications: 0,
        recent_publications: 0,
        nasa_related_count: 0,
        nasa_related_percent: 0,
        total_authors: 0,
        unique_topics: 0,
      },
      researchAreas: {},
      knowledgeGaps: {},
      insights: [],
      analytics: {
        trends: { labels: [], publications: [] },
      },
    };
  }

  // Create and initialize app
  const app = new NASASpaceHubApp(serverData);
  app.initialize();

  // Make app available globally for debugging
  (window as any).app = app;

  console.log("NASA Space Hub loaded");
});
