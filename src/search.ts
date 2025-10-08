// Search functionality

import { APIService } from "./api";
import { StorageService } from "./storage";
import { ToastService } from "./toast";
import { SearchResult, SavedArticle } from "./types";

export class SearchController {
  private apiService: APIService;
  private storageService: StorageService;
  private toastService: ToastService;
  private searchTimeout: number | null = null;
  private searchInput: HTMLInputElement | null = null;
  private resultsContainer: HTMLElement | null = null;

  constructor(
    apiService: APIService,
    storageService: StorageService,
    toastService: ToastService
  ) {
    this.apiService = apiService;
    this.storageService = storageService;
    this.toastService = toastService;
  }

  /**
   * Initialize search functionality
   */
  initialize(): void {
    this.searchInput = document.getElementById(
      "search-input"
    ) as HTMLInputElement;
    this.resultsContainer = document.getElementById("search-results");

    if (!this.searchInput || !this.resultsContainer) {
      console.error("Search elements not found");
      return;
    }

    // Setup search input listener
    this.searchInput.addEventListener("input", (e) => {
      this.handleSearchInput((e.target as HTMLInputElement).value);
    });

    console.log("Search controller initialized");
  }

  /**
   * Handle search input with debouncing
   */
  private handleSearchInput(value: string): void {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    this.searchTimeout = window.setTimeout(() => {
      const query = value.trim();
      if (query.length > 2) {
        this.performSearch(query);
      }
    }, 500);
  }

  /**
   * Perform search
   */
  private async performSearch(query: string): Promise<void> {
    if (!this.resultsContainer) return;

    try {
      // Show loading state
      this.resultsContainer.innerHTML = "<p>Searching...</p>";

      const results = await this.apiService.search(query, 20);
      this.displayResults(results, query);
    } catch (error) {
      console.error("Search error:", error);
      this.resultsContainer.innerHTML =
        '<p style="color: var(--danger);">Error performing search. Please try again.</p>';
      this.toastService.error("Search failed. Please try again.");
    }
  }

  /**
   * Display search results
   */
  // controllers/SearchController.ts - Corrected Code

  /**
   * Display search results
   */
  private displayResults(results: SearchResult[], query: string): void {
    if (!this.resultsContainer) return;

    // Case 1: No results were found
    if (results.length === 0) {
      this.resultsContainer.innerHTML = `
        <p style="text-align: center; color: var(--text-muted); margin-top: 20px;">
            No publications found for "${this.escapeHtml(query)}".
        </p>`;
      return;
    }

    // Case 2: Results were found, so render them
    this.resultsContainer.innerHTML = `
      <h3 style="margin-bottom: 15px;">Found ${
        results.length
      } results for "${this.escapeHtml(query)}"</h3>
      <div class="publications-list">
          ${results.map((pub) => this.createPublicationCard(pub)).join("")}
      </div>
  `;

    // Attach event listeners to the new 'Save Article' buttons
    results.forEach((pub) => {
      const btn = document.getElementById(`save-btn-${pub.article_id}`);
      if (btn) {
        btn.addEventListener("click", () => this.saveArticle(pub));
      }
    });
  }

  /**
   * Create publication card HTML
   */
  private createPublicationCard(pub: SearchResult): string {
    const isAlreadySaved = this.storageService.isArticleSaved(pub.article_id);

    return `
            <div class="card" style="margin-bottom: 15px;">
                <div class="card-header">
                    <div class="card-title" style="font-size: 1rem;">${this.escapeHtml(
                      pub.title
                    )}</div>
                </div>
                <div class="card-content">
                    <p><strong>PMCID:</strong> 
                        <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/${
                          pub.pmcid
                        }/" target="_blank" style="color: var(--accent); text-decoration: none;">${
      pub.pmcid
    }</a>
                        | <strong>Section:</strong> ${pub.section}
                    </p>
                    <p style="margin-top: 10px; color: var(--text-light);">${this.escapeHtml(
                      pub.snippet
                    )}</p>
                    <p style="margin-top: 10px; font-size: 0.85rem;">
                        <strong>Relevance:</strong> ${(
                          pub.relevance_score * 100
                        ).toFixed(1)}%
                        ${
                          pub.journal
                            ? ` | <strong>Journal:</strong> ${this.escapeHtml(
                                pub.journal
                              )}`
                            : ""
                        }
                        ${
                          pub.publication_date
                            ? ` | <strong>Date:</strong> ${pub.publication_date}`
                            : ""
                        }
                    </p>
                    ${
                      pub.keywords && pub.keywords.length > 0
                        ? `
                        <div style="margin-top: 12px;">
                            <strong style="font-size: 0.85rem;">Keywords:</strong>
                            <div style="margin-top: 5px; display: flex; flex-wrap: wrap; gap: 6px;">
                                ${pub.keywords
                                  .map(
                                    (keyword) => `
                                    <span style="display: inline-block; padding: 4px 10px; background: #e6f2ff; color: var(--accent); border-radius: 12px; font-size: 0.8rem; font-weight: 500;">
                                        ${this.escapeHtml(keyword)}
                                    </span>
                                `
                                  )
                                  .join("")}
                            </div>
                        </div>
                    `
                        : ""
                    }
                    <div style="margin-top: 15px; display: flex; gap: 10px;">
                        <button id="save-btn-${pub.article_id}"
                                ${isAlreadySaved ? "disabled" : ""}
                                style="padding: 8px 16px; background: ${
                                  isAlreadySaved ? "#a0aec0" : "var(--accent)"
                                }; color: white; border: none; border-radius: 5px; cursor: ${
      isAlreadySaved ? "not-allowed" : "pointer"
    }; font-size: 0.9rem; display: flex; align-items: center; gap: 6px;">
                            <i class="fas fa-bookmark"></i>
                            ${isAlreadySaved ? "Already Saved" : "Save Article"}
                        </button>
                        <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/${
                          pub.pmcid
                        }/" target="_blank" 
                           style="padding: 8px 16px; background: var(--secondary); color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 0.9rem; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;">
                            <i class="fas fa-external-link-alt"></i>
                            View Full Article
                        </a>
                    </div>
                </div>
            </div>
        `;
  }

  /**
   * Save an article
   */
  private saveArticle(pub: SearchResult): void {
    const article: SavedArticle = {
      id: pub.article_id,
      pmcid: pub.pmcid,
      title: pub.title,
      snippet: pub.snippet,
      link: `https://www.ncbi.nlm.nih.gov/pmc/articles/${pub.pmcid}/`,
      journal: pub.journal,
      date: pub.publication_date,
    };

    const success = this.storageService.saveArticle(article);

    if (success) {
      this.toastService.success(`Article ${pub.pmcid} saved successfully!`);

      // Update the button
      const btn = document.getElementById(
        `save-btn-${pub.article_id}`
      ) as HTMLButtonElement;
      if (btn) {
        btn.disabled = true;
        btn.style.background = "#a0aec0";
        btn.style.cursor = "not-allowed";
        btn.innerHTML = '<i class="fas fa-bookmark"></i> Already Saved';
      }
    } else {
      this.toastService.warning(`Article ${pub.pmcid} is already saved.`);
    }
  }

  /**
   * Escape HTML to prevent XSS
   */
  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Cleanup
   */
  destroy(): void {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
  }
}
