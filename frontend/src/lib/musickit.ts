import { fetchDeveloperToken } from "./api";

declare global {
  interface Window {
    MusicKit: typeof MusicKit;
  }
}

declare namespace MusicKit {
  function configure(config: {
    developerToken: string;
    app: { name: string; build: string };
  }): Promise<MusicKitInstance>;

  function getInstance(): MusicKitInstance;

  interface MusicKitInstance {
    authorize(): Promise<string>;
    unauthorize(): Promise<void>;
    isAuthorized: boolean;
    musicUserToken: string;
    play(): Promise<void>;
    pause(): void;
    stop(): void;
    setQueue(options: { song: string }): Promise<void>;
  }
}

let instance: MusicKit.MusicKitInstance | null = null;

export async function initMusicKit(): Promise<MusicKit.MusicKitInstance> {
  if (instance) return instance;

  const token = await fetchDeveloperToken();

  await loadMusicKitScript();

  instance = await window.MusicKit.configure({
    developerToken: token,
    app: { name: "Folio", build: "1.0.0" },
  });

  return instance;
}

export async function authorizeMusicKit(): Promise<string> {
  const mk = await initMusicKit();
  if (mk.isAuthorized) return mk.musicUserToken;
  return mk.authorize();
}

export function getMusicUserToken(): string | null {
  return instance?.musicUserToken || null;
}

function loadMusicKitScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.MusicKit) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = "https://js-cdn.music.apple.com/musickit/v3/musickit.js";
    script.crossOrigin = "anonymous";
    script.async = true;
    script.onload = () => {
      const check = setInterval(() => {
        if (window.MusicKit) {
          clearInterval(check);
          resolve();
        }
      }, 50);
    };
    script.onerror = () => reject(new Error("Failed to load MusicKit JS"));
    document.head.appendChild(script);
  });
}
