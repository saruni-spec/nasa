// controllers/NavigationController.ts - Navigation and tab management

import { DashboardController } from "./dashboard";
import { SearchController } from "./search";
import { ChatbotController } from "./chatbot";
import { KnowledgeGraphController } from "./knowledgegraph";
import { SavedArticlesController } from "./save_articles";
import { TabId } from "./types";

export class NavigationController {
  private dashboardController: DashboardController;
  private searchController: SearchController;
  private chatbotController: ChatbotController;
  private knowledgeGraphController: KnowledgeGraphController;
  private savedArticlesController: SavedArticlesController;
  private currentTab: TabId = "dashboard";

  constructor(
    dashboardController: DashboardController,
    searchController: SearchController,
    chatbotController: ChatbotController,
    knowledgeGraphController: KnowledgeGraphController,
    savedArticlesController: SavedArticlesController
  ) {
    this.dashboardController = dashboardController;
    this.searchController = searchController;
    this.chatbotController = chatbotController;
    this.knowledgeGraphController = knowledgeGraphController;
    this.savedArticlesController = savedArticlesController;
  }

  /**
   * Initialize navigation
   */
  initialize(): void {
    this.setupNavLinks();
    console.log("Navigation controller initialized");
  }

  /**
   * Setup navigation links
   */
  private setupNavLinks(): void {
    const navLinks = document.querySelectorAll(".nav-link");

    navLinks.forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();

        const tabId = link.getAttribute("data-tab") as TabId;
        if (tabId) {
          this.switchTab(tabId);
        }
      });
    });
  }

  /**
   * Switch to a different tab
   */
  async switchTab(tabId: TabId): Promise<void> {
    // Update active nav link
    document.querySelectorAll(".nav-link").forEach((link) => {
      link.classList.remove("active");
      if (link.getAttribute("data-tab") === tabId) {
        link.classList.add("active");
      }
    });

    // Hide all tab contents
    document.querySelectorAll(".tab-content").forEach((content) => {
      content.classList.remove("active");
    });

    // Show selected tab content
    const tabElement = document.getElementById(`${tabId}-tab`);
    if (tabElement) {
      tabElement.classList.add("active");
    }

    // Update page title
    const navLink = document.querySelector(`[data-tab="${tabId}"]`);
    if (navLink) {
      const titleSpan = navLink.querySelector("span");
      if (titleSpan) {
        this.updatePageTitle(titleSpan.textContent || "");
      }
    }

    // Load tab-specific data
    await this.loadTabData(tabId);

    this.currentTab = tabId;
  }

  /**
   * Load data for specific tab
   */
  private async loadTabData(tabId: TabId): Promise<void> {
    switch (tabId) {
      case "dashboard":
        await this.dashboardController.initialize();
        break;

      case "explore":
        this.searchController.initialize();
        break;

      case "knowledge-graph":
        this.knowledgeGraphController.initialize();
        break;

      case "saved-articles":
        this.savedArticlesController.initialize();
        break;

      case "analytics":
        // Analytics tab (if needed in future)
        break;
    }
  }

  /**
   * Update page title
   */
  private updatePageTitle(title: string): void {
    const pageTitle = document.getElementById("page-title");
    if (pageTitle) {
      pageTitle.textContent = title;
    }
  }

  /**
   * Get current tab
   */
  getCurrentTab(): TabId {
    return this.currentTab;
  }

  /**
   * Programmatically navigate to a tab
   */
  navigateTo(tabId: TabId): void {
    this.switchTab(tabId);
  }
}
