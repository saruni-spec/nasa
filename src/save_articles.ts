// Saved articles management

import { StorageService } from "./storage";
import { ToastService } from "./toast";
import { SavedArticle } from "./types";

export class SavedArticlesController {
  private storageService: StorageService;
  private toastService: ToastService;
  private container: HTMLElement | null = null;

  constructor(storageService: StorageService, toastService: ToastService) {
    this.storageService = storageService;
    this.toastService = toastService;
  }

  /**
   * Initialize saved articles view
   */
  initialize(): void {
    this.container = document.getElementById("saved-articles-list");

    if (!this.container) {
      console.error("Saved articles container not found");
      return;
    }

    this.displaySavedArticles();
    console.log("Saved articles controller initialized");
  }

  /**
   * Display saved articles
   */
  displaySavedArticles(): void {
    if (!this.container) return;

    const savedArticles = this.storageService.getSavedArticles();

    if (savedArticles.length === 0) {
      this.container.innerHTML =
        '<p style="color: var(--text-muted);">You have not saved any articles yet.</p>';
      return;
    }

    this.container.innerHTML = savedArticles
      .map((article, index) => this.createArticleCard(article, index))
      .join("");

    // Attach event listeners to remove buttons
    savedArticles.forEach((article, index) => {
      const btn = document.getElementById(`remove-btn-${index}`);
      if (btn) {
        btn.addEventListener("click", () => this.removeArticle(index));
      }
    });
  }

  /**
   * Create article card HTML
   */
  private createArticleCard(article: SavedArticle, index: number): string {
    return `
            <div class="card" style="margin-bottom: 15px;">
                <div class="card-header">
                    <div class="card-title" style="font-size: 1rem;">${this.escapeHtml(
                      article.title
                    )}</div>
                </div>
                <div class="card-content">
                    <p><strong>PMCID:</strong> 
                        <a href="${
                          article.link
                        }" target="_blank" style="color: var(--accent); text-decoration: none;">${
      article.pmcid
    }</a>
                        ${
                          article.journal
                            ? ` | <strong>Journal:</strong> ${this.escapeHtml(
                                article.journal
                              )}`
                            : ""
                        }
                        ${
                          article.date
                            ? ` | <strong>Date:</strong> ${article.date}`
                            : ""
                        }
                    </p>
                    <p style="margin-top: 10px; color: var(--text-light);">${this.escapeHtml(
                      article.snippet
                    )}</p>
                    <div style="margin-top: 15px; display: flex; gap: 10px;">
                        <button id="remove-btn-${index}"
                                style="padding: 8px 16px; background: var(--danger); color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 0.9rem; display: flex; align-items: center; gap: 6px;">
                            <i class="fas fa-trash"></i>
                            Remove
                        </button>
                        <a href="${article.link}" target="_blank" 
                           style="padding: 8px 16px; background: var(--secondary); color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 0.9rem; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;">
                            <i class="fas fa-external-link-alt"></i>
                            View Article
                        </a>
                    </div>
                </div>
            </div>
        `;
  }

  /**
   * Remove an article
   */
  private removeArticle(index: number): void {
    const savedArticles = this.storageService.getSavedArticles();
    const article = savedArticles[index];

    if (!article) return;

    if (confirm(`Remove "${article.pmcid}" from saved articles?`)) {
      const success = this.storageService.removeArticle(index);

      if (success) {
        this.toastService.success(`Article ${article.pmcid} removed`);
        this.displaySavedArticles();
      } else {
        this.toastService.error("Failed to remove article");
      }
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
   * Refresh the view
   */
  refresh(): void {
    this.displaySavedArticles();
  }

  /**
   * Cleanup
   */
  destroy(): void {
    console.log("Saved articles controller destroyed");
  }
}
