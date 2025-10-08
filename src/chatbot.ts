// Chatbot management

import { APIService } from "./api";
import { StorageService } from "./storage";
import { ToastService } from "./toast";
import { ChatMessage } from "./types";

export class ChatbotController {
  private apiService: APIService;
  private storageService: StorageService;
  private toastService: ToastService;
  private chatWindow: HTMLElement | null = null;
  private chatMessages: HTMLElement | null = null;
  private chatInput: HTMLInputElement | null = null;
  private sendBtn: HTMLElement | null = null;
  private closeBtn: HTMLElement | null = null;
  private clearBtn: HTMLElement | null = null;
  private chatbotModel: HTMLElement | null = null;

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
   * Initialize chatbot
   */
  initialize(): void {
    this.chatWindow = document.getElementById("chatWindow");
    this.chatMessages = document.getElementById("chatMessages");
    this.chatInput = document.getElementById("chatInput") as HTMLInputElement;
    this.sendBtn = document.getElementById("sendBtn");
    this.closeBtn = document.getElementById("closeChat");
    this.clearBtn = document.getElementById("clearChat");
    this.chatbotModel = document.querySelector("model-viewer");

    if (
      !this.chatWindow ||
      !this.chatMessages ||
      !this.chatInput ||
      !this.sendBtn
    ) {
      console.error("Chatbot elements not found");
      return;
    }

    this.setupEventListeners();
    this.loadChatHistory();

    console.log("Chatbot controller initialized");
  }

  /**
   * Setup event listeners
   */
  private setupEventListeners(): void {
    // Open chat window
    if (this.chatbotModel) {
      this.chatbotModel.addEventListener("click", () => this.openChat());
    }

    // Close chat window
    if (this.closeBtn) {
      this.closeBtn.addEventListener("click", () => this.closeChat());
    }

    // Clear chat history
    if (this.clearBtn) {
      this.clearBtn.addEventListener("click", () => this.clearHistory());
    }

    // Send message
    if (this.sendBtn) {
      this.sendBtn.addEventListener("click", () => this.sendMessage());
    }

    // Send on Enter key
    if (this.chatInput) {
      this.chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          this.sendMessage();
        }
      });
    }
  }

  /**
   * Load chat history from storage
   */
  private loadChatHistory(): void {
    const history = this.storageService.getChatHistory();

    if (history.length === 0) {
      this.addMessage(
        "👋 I'm Titan, your guide to life in space. What shall we explore?",
        "bot",
        false
      );
    } else {
      history.forEach((msg) => {
        this.addMessage(msg.text, msg.sender, false);
      });
    }
  }

  /**
   * Open chat window
   */
  private openChat(): void {
    if (this.chatWindow) {
      this.chatWindow.classList.add("active");
    }
    if (this.chatbotModel) {
      (this.chatbotModel as any).style.animationPlayState = "paused";
    }
  }

  /**
   * Close chat window
   */
  private closeChat(): void {
    if (this.chatWindow) {
      this.chatWindow.classList.remove("active");
    }
    if (this.chatbotModel) {
      (this.chatbotModel as any).style.animationPlayState = "running";
    }
  }

  /**
   * Clear chat history
   */
  private clearHistory(): void {
    this.storageService.clearChatHistory();
    if (this.chatMessages) {
      this.chatMessages.innerHTML = "";
    }
    this.addMessage(
      "👋 Chat cleared. I'm Titan, your guide to life in space. What shall we explore?",
      "bot",
      true
    );
    this.toastService.info("Chat history cleared");
  }

  /**
   * Send message
   */
  private async sendMessage(): Promise<void> {
    if (!this.chatInput || !this.chatMessages) return;

    const userText = this.chatInput.value.trim();
    if (!userText) return;

    // Add user message
    this.addMessage(userText, "user", true);
    this.chatInput.value = "";

    // Show typing indicator
    const typingDiv = document.createElement("div");
    typingDiv.classList.add("message", "bot");
    typingDiv.textContent = "Titan is thinking...";
    typingDiv.id = "typing-indicator";
    this.chatMessages.appendChild(typingDiv);
    this.scrollToBottom();

    try {
      // Call API
      const response = await this.apiService.sendChatMessage(userText);

      // Remove typing indicator
      const typingIndicator = document.getElementById("typing-indicator");
      if (typingIndicator) {
        typingIndicator.remove();
      }

      // Add bot response
      this.addMessage(response, "bot", true);
    } catch (error) {
      console.error("Chatbot error:", error);

      // Remove typing indicator
      const typingIndicator = document.getElementById("typing-indicator");
      if (typingIndicator) {
        typingIndicator.remove();
      }

      this.addMessage(
        "Sorry, I'm having trouble connecting right now. Please try again.",
        "bot",
        true
      );
      this.toastService.error("Failed to send message. Please try again.");
    }
  }

  /**
   * Add message to chat
   */
  private addMessage(
    text: string,
    sender: "user" | "bot",
    save: boolean = true
  ): void {
    if (!this.chatMessages) return;

    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender);
    msgDiv.textContent = text;
    this.chatMessages.appendChild(msgDiv);
    this.scrollToBottom();

    if (save) {
      const message: ChatMessage = {
        text,
        sender,
        timestamp: Date.now(),
      };
      this.storageService.saveChatMessage(message);
    }
  }

  /**
   * Scroll chat to bottom
   */
  private scrollToBottom(): void {
    if (this.chatMessages) {
      this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
  }

  /**
   * Cleanup
   */
  destroy(): void {
    // Remove event listeners if needed
    console.log("Chatbot controller destroyed");
  }
}
