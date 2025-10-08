// services/StorageService.ts - In-memory data storage

import { SavedArticle, ChatMessage } from "./types";

export class StorageService {
  private savedArticles: SavedArticle[] = [];
  private chatHistory: ChatMessage[] = [];

  /**
   * Save an article
   */
  saveArticle(article: SavedArticle): boolean {
    // Check if already saved
    if (this.savedArticles.find((a) => a.id === article.id)) {
      return false; // Already exists
    }

    this.savedArticles.push(article);
    return true;
  }

  /**
   * Get all saved articles
   */
  getSavedArticles(): SavedArticle[] {
    return [...this.savedArticles]; // Return copy
  }

  /**
   * Remove a saved article by index
   */
  removeArticle(index: number): boolean {
    if (index >= 0 && index < this.savedArticles.length) {
      this.savedArticles.splice(index, 1);
      return true;
    }
    return false;
  }

  /**
   * Remove a saved article by ID
   */
  removeArticleById(id: number): boolean {
    const index = this.savedArticles.findIndex((a) => a.id === id);
    if (index !== -1) {
      this.savedArticles.splice(index, 1);
      return true;
    }
    return false;
  }

  /**
   * Check if article is saved
   */
  isArticleSaved(id: number): boolean {
    return this.savedArticles.some((a) => a.id === id);
  }

  /**
   * Get count of saved articles
   */
  getSavedArticlesCount(): number {
    return this.savedArticles.length;
  }

  /**
   * Save a chat message
   */
  saveChatMessage(message: ChatMessage): void {
    this.chatHistory.push(message);
  }

  /**
   * Get chat history
   */
  getChatHistory(): ChatMessage[] {
    return [...this.chatHistory]; // Return copy
  }

  /**
   * Clear chat history
   */
  clearChatHistory(): void {
    this.chatHistory = [];
  }

  /**
   * Clear all data
   */
  clearAll(): void {
    this.savedArticles = [];
    this.chatHistory = [];
  }
}
