/**
 * LLM Client using Vercel AI SDK.
 *
 * Provides a unified interface for calling multiple AI providers
 * (OpenAI, Anthropic, DeepSeek, Google) through the Vercel AI SDK.
 *
 * Falls back to direct HTTP calls if the AI SDK is not installed.
 */

import { EventEmitter } from 'events';

export interface LLMConfig {
  provider: string;
  apiKey: string;
  baseUrl?: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
}

export interface LLMResponse {
  text: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

// Try to load AI SDK modules
let generateTextFn: any = null;
let streamTextFn: any = null;
let createOpenAIFn: any = null;
let createAnthropicFn: any = null;
let createGoogleFn: any = null;
let createDeepSeekFn: any = null;

try {
  const ai = require('ai');
  generateTextFn = ai.generateText;
  streamTextFn = ai.streamText;
} catch { /* ai not installed */ }

try { createOpenAIFn = require('@ai-sdk/openai').createOpenAI; } catch { /* not installed */ }
try { createAnthropicFn = require('@ai-sdk/anthropic').createAnthropic; } catch { /* not installed */ }
try { createGoogleFn = require('@ai-sdk/google').createGoogle; } catch { /* not installed */ }
try { createDeepSeekFn = require('@ai-sdk/deepseek').createDeepSeek; } catch { /* not installed */ }

function createProvider(config: LLMConfig): any {
  switch (config.provider) {
    case 'openai':
      if (createOpenAIFn) {
        return createOpenAIFn({
          apiKey: config.apiKey,
          baseURL: config.baseUrl,
        });
      }
      break;
    case 'anthropic':
      if (createAnthropicFn) {
        return createAnthropicFn({ apiKey: config.apiKey });
      }
      break;
    case 'google':
      if (createGoogleFn) {
        return createGoogleFn({ apiKey: config.apiKey });
      }
      break;
    case 'deepseek':
      if (createDeepSeekFn) {
        return createDeepSeekFn({
          apiKey: config.apiKey,
          baseURL: config.baseUrl,
        });
      }
      break;
  }
  return null;
}

export class LLMClient extends EventEmitter {
  private config: LLMConfig;
  private provider: any;

  constructor(config: LLMConfig) {
    super();
    this.config = config;
    this.provider = createProvider(config);
  }

  async generate(prompt: string, system?: string): Promise<string> {
    // Try Vercel AI SDK first
    if (this.provider && generateTextFn) {
      try {
        const result = await generateTextFn({
          model: this.provider(this.config.model),
          system: system || `你是${this.config.provider}助手。`,
          prompt,
          maxTokens: this.config.maxTokens ?? 4096,
          temperature: this.config.temperature ?? 0.7,
        });
        return result.text;
      } catch (err: any) {
        this.emit('error', { error: err.message, provider: this.config.provider });
        throw err;
      }
    }

    // Fallback: direct HTTP call (OpenAI-compatible API)
    return this.fallbackGenerate(prompt, system);
  }

  private async fallbackGenerate(prompt: string, system?: string): Promise<string> {
    const baseUrl = this.config.baseUrl || 'https://api.openai.com/v1';
    const url = `${baseUrl.replace(/\/$/, '')}/chat/completions`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        model: this.config.model,
        messages: [
          { role: 'system', content: system || `你是${this.config.provider}助手。` },
          { role: 'user', content: prompt },
        ],
        max_tokens: this.config.maxTokens ?? 4096,
        temperature: this.config.temperature ?? 0.7,
      }),
    });

    if (!response.ok) {
      throw new Error(`LLM API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as any;
    return data.choices[0].message.content.trim();
  }

  stream(prompt: string, system?: string): any {
    if (this.provider && streamTextFn) {
      return streamTextFn({
        model: this.provider(this.config.model),
        system: system || `你是${this.config.provider}助手。`,
        prompt,
        maxTokens: this.config.maxTokens ?? 4096,
      });
    }
    throw new Error('Streaming requires Vercel AI SDK');
  }
}

export class LLMRegistry {
  private clients: Map<string, LLMClient> = new Map();
  private defaultClient: LLMClient;

  constructor(defaultConfig: LLMConfig, overrides?: Record<string, LLMConfig>) {
    this.defaultClient = new LLMClient(defaultConfig);
    if (overrides) {
      for (const [role, config] of Object.entries(overrides)) {
        // Merge with defaults for missing fields
        const merged: LLMConfig = {
          ...defaultConfig,
          ...config,
        };
        this.clients.set(role, new LLMClient(merged));
      }
    }
  }

  getClient(role: string): LLMClient {
    return this.clients.get(role) || this.defaultClient;
  }

  async generate(role: string, prompt: string, system?: string): Promise<string> {
    return this.getClient(role).generate(prompt, system);
  }
}
