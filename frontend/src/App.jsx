import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { createPortal } from "react-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  ArrowUp,
  Bot,
  Check,
  ChevronRight,
  CircleUserRound,
  Copy,
  Edit3,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  MoreHorizontal,
  Plus,
  Search,
  Shield,
  Square,
  Trash2,
  Upload,
  UserCog,
  Users,
  X,
} from "lucide-react";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://127.0.0.1:8000/api" : "/api");

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem("revilon_access");

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  return config;
});

let refreshRequest = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const refreshToken = localStorage.getItem("revilon_refresh");

    const shouldRefresh =
      error.response?.status === 401 &&
      refreshToken &&
      !originalRequest?._retry &&
      !originalRequest?.url?.includes("token/refresh");

    if (!shouldRefresh) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshRequest) {
        refreshRequest = axios.post(
          `${API_BASE_URL}/auth/token/refresh/`,
          { refresh: refreshToken },
        );
      }

      const response = await refreshRequest;
      refreshRequest = null;

      localStorage.setItem("revilon_access", response.data.access);

      if (response.data.refresh) {
        localStorage.setItem("revilon_refresh", response.data.refresh);
      }

      originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
      return api(originalRequest);
    } catch (refreshError) {
      refreshRequest = null;
      localStorage.removeItem("revilon_access");
      localStorage.removeItem("revilon_refresh");
      window.dispatchEvent(new Event("revilon-auth-expired"));
      return Promise.reject(refreshError);
    }
  },
);


function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  const data = error?.response?.data;

  if (!data) {
    return error?.message || fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  if (data.detail) {
    return data.detail;
  }

  const firstValue = Object.values(data)[0];

  if (Array.isArray(firstValue)) {
    return firstValue[0];
  }

  if (typeof firstValue === "string") {
    return firstValue;
  }

  if (firstValue && typeof firstValue === "object") {
    const nestedValue = Object.values(firstValue)[0];
    if (Array.isArray(nestedValue)) {
      return nestedValue[0];
    }
    if (typeof nestedValue === "string") {
      return nestedValue;
    }
  }

  return fallback;
}


function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false);
  const resetTimerRef = useRef(null);
  const codeElement = Array.isArray(children) ? children[0] : children;
  const languageClass = codeElement?.props?.className || "";
  const language = languageClass.replace(/^language-/, "") || "code";
  const code = String(codeElement?.props?.children || "").replace(/\n$/, "");

  useEffect(() => {
    return () => window.clearTimeout(resetTimerRef.current);
  }, []);

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.clearTimeout(resetTimerRef.current);
      resetTimerRef.current = window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span>{language}</span>
        <button type="button" className="copy-code-button" onClick={copyCode}>
          {copied ? <Check size={14} /> : <Copy size={14} />}
          <span>{copied ? "Copied" : "Copy code"}</span>
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  );
}


function MarkdownMessage({ content }) {
  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre: CodeBlock,
          code: ({ node: _node, className, children, ...props }) => (
            <code className={className} {...props}>
              {children}
            </code>
          ),
          a: ({ node: _node, children, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}


function getDisplayName(user) {
  if (!user) {
    return "Your account";
  }

  const name = `${user.first_name || ""} ${user.last_name || ""}`.trim();
  return name || user.username || "Your account";
}


function getInitials(user) {
  if (!user) {
    return "U";
  }

  const first = user.first_name?.trim()?.[0] || "";
  const last = user.last_name?.trim()?.[0] || "";

  if (first || last) {
    return `${first}${last}`.toUpperCase();
  }

  return user.username?.trim()?.[0]?.toUpperCase() || "U";
}


function formatDate(value) {
  if (!value) {
    return "Never";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}


function Avatar({ user, size = "medium" }) {
  return (
    <span className={`avatar avatar-${size}`}>
      {user?.profile_picture ? (
        <img src={user.profile_picture} alt="" />
      ) : (
        <span>{getInitials(user)}</span>
      )}
    </span>
  );
}


function Modal({ children, onClose, className = "" }) {
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section
        className={`modal-panel ${className}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        {children}
      </section>
    </div>
  );
}


function AccountMenu({
  user,
  onProfile,
  onPassword,
  onAdmin,
  onChat,
  onLogout,
  adminPage = false,
}) {
  return (
    <div className="account-popover">
      <div className="account-popover-header">
        <Avatar user={user} size="large" />
        <div>
          <strong>{getDisplayName(user)}</strong>
          <span>@{user?.username}</span>
        </div>
      </div>

      <div className="account-menu-divider" />

      {!adminPage && (
        <button type="button" onClick={onProfile}>
          <CircleUserRound size={17} />
          <span>Profile</span>
        </button>
      )}

      {!adminPage && (
        <button type="button" onClick={onPassword}>
          <KeyRound size={17} />
          <span>Change password</span>
        </button>
      )}

      {user?.is_staff && !adminPage && (
        <button type="button" onClick={onAdmin}>
          <LayoutDashboard size={17} />
          <span>Admin dashboard</span>
        </button>
      )}

      {adminPage && (
        <button type="button" onClick={onChat}>
          <MessageSquare size={17} />
          <span>Open Revilon AI</span>
        </button>
      )}

      <div className="account-menu-divider" />

      <button type="button" onClick={onLogout}>
        <LogOut size={17} />
        <span>Log out</span>
      </button>
    </div>
  );
}


function App() {
  const [path, setPath] = useState(window.location.pathname);
  const [booting, setBooting] = useState(true);
  const [user, setUser] = useState(null);
  const [landingMessage, setLandingMessage] = useState("");

  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authForm, setAuthForm] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [verificationOpen, setVerificationOpen] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [verificationBusy, setVerificationBusy] = useState(false);
  const [verificationError, setVerificationError] = useState("");
  const [verificationMessage, setVerificationMessage] = useState("");

  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageText, setMessageText] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState("");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [conversationMenu, setConversationMenu] = useState(null);
  const [deleteConversation, setDeleteConversation] = useState(null);
  const [renameConversation, setRenameConversation] = useState(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);

  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profilePictureFile, setProfilePictureFile] = useState(null);
  const [profilePreview, setProfilePreview] = useState(null);
  const [removeProfilePicture, setRemoveProfilePicture] = useState(false);
  const [profileForm, setProfileForm] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
  });

  const [passwordOpen, setPasswordOpen] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [adminUsers, setAdminUsers] = useState([]);
  const [adminStats, setAdminStats] = useState({
    total_users: 0,
    active_users: 0,
    administrators: 0,
    new_users: 0,
  });
  const [adminSearch, setAdminSearch] = useState("");
  const [adminBusy, setAdminBusy] = useState(false);
  const [adminError, setAdminError] = useState("");
  const [selectedAdminUser, setSelectedAdminUser] = useState(null);
  const [adminEditForm, setAdminEditForm] = useState(null);
  const [adminActionBusy, setAdminActionBusy] = useState(false);
  const [adminActionError, setAdminActionError] = useState("");
  const [adminDeleteUser, setAdminDeleteUser] = useState(null);

  const messageEndRef = useRef(null);
  const profileFileRef = useRef(null);
  const chatAbortControllerRef = useRef(null);

  const isAuthenticated = Boolean(user);
  const isAdminPage = path === "/admin";

  useEffect(() => {
    const viewport = window.visualViewport;
    const updateAppHeight = () => {
      const height = viewport?.height || window.innerHeight;
      document.documentElement.style.setProperty("--app-height", `${height}px`);
    };

    updateAppHeight();
    window.addEventListener("resize", updateAppHeight);
    window.addEventListener("orientationchange", updateAppHeight);
    viewport?.addEventListener("resize", updateAppHeight);

    return () => {
      window.removeEventListener("resize", updateAppHeight);
      window.removeEventListener("orientationchange", updateAppHeight);
      viewport?.removeEventListener("resize", updateAppHeight);
      document.documentElement.style.removeProperty("--app-height");
    };
  }, []);

  const navigate = (nextPath) => {
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
    setAccountMenuOpen(false);
    setMobileSidebarOpen(false);
  };

  const clearSession = () => {
    localStorage.removeItem("revilon_access");
    localStorage.removeItem("revilon_refresh");
    setUser(null);
    setConversations([]);
    setActiveConversation(null);
    setMessages([]);
    setAccountMenuOpen(false);
  };

  const loadConversations = async () => {
    try {
      const response = await api.get("/chat/conversations/");
      setConversations(response.data.results || response.data || []);
    } catch (error) {
      if (error.response?.status !== 401) {
        setChatError(getErrorMessage(error));
      }
    }
  };

  useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname);
    const handleExpired = () => {
      clearSession();
      navigate("/");
      setAuthMode("login");
      setAuthOpen(true);
      setAuthError("Your session expired. Please sign in again.");
    };

    window.addEventListener("popstate", handlePopState);
    window.addEventListener("revilon-auth-expired", handleExpired);

    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("revilon-auth-expired", handleExpired);
    };
  }, []);

  useEffect(() => {
    const bootstrap = async () => {
      const accessToken = localStorage.getItem("revilon_access");

      if (!accessToken) {
        setBooting(false);
        return;
      }

      try {
        const response = await api.get("/auth/profile/");
        setUser(response.data);

        if (window.location.pathname === "/admin" && !response.data.is_staff) {
          navigate("/");
        }
      } catch {
        clearSession();
        navigate("/");
      } finally {
        setBooting(false);
      }
    };

    bootstrap();
  }, []);

  useEffect(() => {
    if (user && !isAdminPage) {
      loadConversations();
    }
  }, [user?.id, isAdminPage]);

  useEffect(() => {
    if (user && isAdminPage && !user.is_staff) {
      navigate("/");
    }
  }, [user?.id, user?.is_staff, isAdminPage]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatBusy]);

  const loadAdminUsers = async (searchValue = "") => {
    if (!user?.is_staff) {
      return;
    }

    setAdminBusy(true);
    setAdminError("");

    try {
      const response = await api.get("/auth/admin/users/", {
        params: searchValue ? { search: searchValue } : {},
      });
      setAdminUsers(response.data.users || []);
      setAdminStats(response.data.stats || {});
    } catch (error) {
      setAdminError(getErrorMessage(error, "Could not load users."));
    } finally {
      setAdminBusy(false);
    }
  };

  useEffect(() => {
    if (!isAdminPage || !user?.is_staff) {
      return undefined;
    }

    const timeout = window.setTimeout(() => {
      loadAdminUsers(adminSearch);
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [isAdminPage, user?.is_staff, adminSearch]);

  useEffect(() => {
    return () => {
      if (profilePreview?.startsWith("blob:")) {
        URL.revokeObjectURL(profilePreview);
      }
    };
  }, [profilePreview]);

  useEffect(() => () => {
    chatAbortControllerRef.current?.abort();
  }, []);

  const openAuth = (mode) => {
    setAuthMode(mode);
    setAuthError("");
    setAuthForm({
      first_name: "",
      last_name: "",
      username: "",
      email: "",
      password: "",
      confirm_password: "",
    });
    setVerificationOpen(false);
    setAuthOpen(true);
  };

  const openVerification = (email, message = "") => {
    setAuthOpen(false);
    setVerificationEmail(email || "");
    setVerificationCode("");
    setVerificationError("");
    setVerificationMessage(message);
    setVerificationOpen(true);
  };

  const saveTokens = (data) => {
    localStorage.setItem("revilon_access", data.access);
    localStorage.setItem("revilon_refresh", data.refresh);
  };

  const submitAuth = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");

    if (
      authMode === "register" &&
      authForm.password !== authForm.confirm_password
    ) {
      setAuthError("The password confirmation does not match.");
      setAuthBusy(false);
      return;
    }

    try {
      const endpoint = authMode === "login" ? "/auth/login/" : "/auth/register/";
      const payload =
        authMode === "login"
          ? {
              username: authForm.username,
              password: authForm.password,
            }
          : {
              first_name: authForm.first_name,
              last_name: authForm.last_name,
              username: authForm.username,
              email: authForm.email,
              password: authForm.password,
            };

      const response = await api.post(endpoint, payload);

      if (response.data.verification_required) {
        openVerification(
          response.data.email,
          response.data.message || "A verification code was sent to your email.",
        );
        return;
      }

      saveTokens(response.data);
      setUser(response.data.user);
      setAuthOpen(false);

      if (response.data.user.is_staff) {
        navigate("/admin");
      } else {
        if (landingMessage.trim()) {
          setMessageText(landingMessage.trim());
          setLandingMessage("");
        }
        navigate("/");
      }
    } catch (error) {
      if (error.response?.data?.code === "email_not_verified") {
        openVerification(
          error.response.data.email,
          "Enter the verification code sent when you registered.",
        );
        return;
      }

      setAuthError(getErrorMessage(error));
    } finally {
      setAuthBusy(false);
    }
  };

  const submitVerification = async (event) => {
    event.preventDefault();

    if (!/^\d{6}$/.test(verificationCode)) {
      setVerificationError("Enter the six-digit verification code.");
      return;
    }

    setVerificationBusy(true);
    setVerificationError("");
    setVerificationMessage("");

    try {
      const response = await api.post("/auth/verify-email/", {
        email: verificationEmail,
        code: verificationCode,
      });

      saveTokens(response.data);
      setUser(response.data.user);
      setVerificationOpen(false);

      if (response.data.user.is_staff) {
        navigate("/admin");
      } else {
        if (landingMessage.trim()) {
          setMessageText(landingMessage.trim());
          setLandingMessage("");
        }
        navigate("/");
      }
    } catch (error) {
      setVerificationError(
        getErrorMessage(error, "The code could not be verified."),
      );
    } finally {
      setVerificationBusy(false);
    }
  };

  const resendVerification = async () => {
    setVerificationBusy(true);
    setVerificationError("");
    setVerificationMessage("");

    try {
      const response = await api.post("/auth/resend-verification/", {
        email: verificationEmail,
      });
      setVerificationCode("");
      setVerificationMessage(response.data.message || "A new code was sent.");
    } catch (error) {
      setVerificationError(
        getErrorMessage(error, "A new code could not be sent."),
      );
    } finally {
      setVerificationBusy(false);
    }
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("revilon_refresh");

    try {
      if (refreshToken) {
        await api.post("/auth/logout/", { refresh: refreshToken });
      }
    } catch {
      // The local session is cleared even if the server token already expired.
    }

    clearSession();
    navigate("/");
  };

  const startNewConversation = () => {
    setActiveConversation(null);
    setMessages([]);
    setChatError("");
    setConversationMenuId(null);
    setMobileSidebarOpen(false);
  };

  const selectConversation = async (conversation) => {
    setChatError("");
    setConversationMenuId(null);
    setMobileSidebarOpen(false);

    try {
      const response = await api.get(`/chat/conversations/${conversation.id}/`);
      setActiveConversation(response.data);
      setMessages(response.data.messages || []);
    } catch (error) {
      setChatError(getErrorMessage(error, "Could not load this conversation."));
    }
  };

  const sendMessage = async (event) => {
    event?.preventDefault();
    const content = messageText.trim();

    if (!content || chatBusy) {
      return;
    }

    const optimisticMessage = {
      id: `temporary-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setMessageText("");
    setChatError("");
    setMessages((current) => [...current, optimisticMessage]);
    setChatBusy(true);
    const abortController = new AbortController();
    chatAbortControllerRef.current = abortController;

    try {
      const response = await api.post(
        "/chat/messages/",
        {
          content,
          conversation_id: activeConversation?.id || null,
        },
        { signal: abortController.signal },
      );

      const conversation = response.data.conversation;
      setActiveConversation(conversation);
      setMessages(conversation.messages || []);
      await loadConversations();
    } catch (error) {
      if (axios.isCancel(error)) {
        return;
      }

      const savedConversation = error.response?.data?.conversation;

      if (savedConversation) {
        setActiveConversation(savedConversation);
        setMessages(savedConversation.messages || []);
        await loadConversations();
      }

      setChatError(
        getErrorMessage(
          error,
          "Revilon AI could not generate a response. Please try again.",
        ),
      );
    } finally {
      if (chatAbortControllerRef.current === abortController) {
        chatAbortControllerRef.current = null;
      }
      setChatBusy(false);
    }
  };

  const stopGenerating = () => {
    chatAbortControllerRef.current?.abort();
  };

  const confirmDeleteConversation = async () => {
    if (!deleteConversation) {
      return;
    }

    try {
      await api.delete(`/chat/conversations/${deleteConversation.id}/`);
      setConversations((current) =>
        current.filter((item) => item.id !== deleteConversation.id),
      );

      if (activeConversation?.id === deleteConversation.id) {
        startNewConversation();
      }

      setDeleteConversation(null);
    } catch (error) {
      setChatError(getErrorMessage(error, "Could not delete the conversation."));
      setDeleteConversation(null);
    }
  };

  const toggleConversationMenu = (event, conversation) => {
    if (conversationMenu?.id === conversation.id) {
      setConversationMenu(null);
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const menuHeight = 86;
    const top = rect.bottom + menuHeight > window.innerHeight
      ? rect.top - menuHeight - 4
      : rect.bottom + 4;
    setConversationMenu({ id: conversation.id, top, right: window.innerWidth - rect.right });
  };

  const submitRenameConversation = async (event) => {
    event.preventDefault();
    const title = renameTitle.trim();
    if (!renameConversation || !title) return;
    setRenameBusy(true);
    try {
      const response = await api.patch(`/chat/conversations/${renameConversation.id}/`, { title });
      setConversations((current) => current.map((item) =>
        item.id === response.data.id ? { ...item, ...response.data } : item
      ));
      if (activeConversation?.id === response.data.id) {
        setActiveConversation((current) => ({ ...current, ...response.data }));
      }
      setRenameConversation(null);
    } catch (error) {
      setChatError(getErrorMessage(error, "Could not rename the conversation."));
    } finally {
      setRenameBusy(false);
    }
  };

  const openProfile = () => {
    setProfileForm({
      first_name: user?.first_name || "",
      last_name: user?.last_name || "",
      username: user?.username || "",
      email: user?.email || "",
    });
    setProfilePictureFile(null);
    setProfilePreview(user?.profile_picture || null);
    setRemoveProfilePicture(false);
    setProfileError("");
    setAccountMenuOpen(false);
    setProfileOpen(true);
  };

  const chooseProfilePicture = (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (!file.type.startsWith("image/")) {
      setProfileError("Choose a JPG, PNG, or WEBP image.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setProfileError("Profile pictures must be 5 MB or smaller.");
      return;
    }

    if (profilePreview?.startsWith("blob:")) {
      URL.revokeObjectURL(profilePreview);
    }

    setProfilePictureFile(file);
    setProfilePreview(URL.createObjectURL(file));
    setRemoveProfilePicture(false);
    setProfileError("");
  };

  const submitProfile = async (event) => {
    event.preventDefault();
    setProfileBusy(true);
    setProfileError("");

    let latestUser = null;

    try {
      const profileResponse = await api.patch("/auth/profile/", profileForm);
      latestUser = profileResponse.data;

      if (profilePictureFile) {
        const pictureData = new FormData();
        pictureData.append("profile_picture", profilePictureFile);
        const pictureResponse = await api.post(
          "/auth/profile/picture/",
          pictureData,
        );
        latestUser = pictureResponse.data;
      } else if (removeProfilePicture) {
        const pictureResponse = await api.delete("/auth/profile/picture/");
        latestUser = pictureResponse.data;
      }

      setUser(latestUser);
      setProfileOpen(false);
    } catch (error) {
      if (latestUser) {
        setUser(latestUser);
      }
      setProfileError(getErrorMessage(error, "Could not update your profile."));
    } finally {
      setProfileBusy(false);
    }
  };

  const openPassword = () => {
    setPasswordForm({
      current_password: "",
      new_password: "",
      confirm_password: "",
    });
    setPasswordError("");
    setPasswordSuccess("");
    setAccountMenuOpen(false);
    setPasswordOpen(true);
  };

  const submitPassword = async (event) => {
    event.preventDefault();
    setPasswordBusy(true);
    setPasswordError("");
    setPasswordSuccess("");

    try {
      const response = await api.post("/auth/change-password/", passwordForm);
      setPasswordSuccess(response.data.message);

      window.setTimeout(() => {
        clearSession();
        setPasswordOpen(false);
        navigate("/");
        openAuth("login");
      }, 1200);
    } catch (error) {
      setPasswordError(getErrorMessage(error, "Could not change your password."));
    } finally {
      setPasswordBusy(false);
    }
  };

  const openAdminUser = (adminUser) => {
    setSelectedAdminUser(adminUser);
    setAdminEditForm({
      first_name: adminUser.first_name || "",
      last_name: adminUser.last_name || "",
      username: adminUser.username || "",
      email: adminUser.email || "",
      is_active: adminUser.is_active,
      is_staff: adminUser.is_staff,
    });
    setAdminActionError("");
  };

  const saveAdminUser = async (event) => {
    event.preventDefault();
    setAdminActionBusy(true);
    setAdminActionError("");

    try {
      const response = await api.patch(
        `/auth/admin/users/${selectedAdminUser.id}/`,
        adminEditForm,
      );

      setAdminUsers((current) =>
        current.map((item) =>
          item.id === response.data.id ? response.data : item,
        ),
      );

      if (response.data.id === user.id) {
        const profileResponse = await api.get("/auth/profile/");
        setUser(profileResponse.data);
      }

      setSelectedAdminUser(null);
      setAdminEditForm(null);
      await loadAdminUsers(adminSearch);
    } catch (error) {
      setAdminActionError(getErrorMessage(error, "Could not update this user."));
    } finally {
      setAdminActionBusy(false);
    }
  };

  const deleteAdminUser = async () => {
    if (!adminDeleteUser) {
      return;
    }

    setAdminActionBusy(true);
    setAdminActionError("");

    try {
      await api.delete(`/auth/admin/users/${adminDeleteUser.id}/`);
      setAdminDeleteUser(null);
      await loadAdminUsers(adminSearch);
    } catch (error) {
      setAdminActionError(getErrorMessage(error, "Could not delete this user."));
    } finally {
      setAdminActionBusy(false);
    }
  };

  const conversationTitle = activeConversation?.title || "New conversation";

  const adminSummary = useMemo(
    () => [
      {
        label: "Total users",
        value: adminStats.total_users || 0,
        icon: Users,
      },
      {
        label: "Active accounts",
        value: adminStats.active_users || 0,
        icon: Check,
      },
      {
        label: "Administrators",
        value: adminStats.administrators || 0,
        icon: Shield,
      },
      {
        label: "New this month",
        value: adminStats.new_users || 0,
        icon: UserCog,
      },
    ],
    [adminStats],
  );

  if (booting) {
    return (
      <div className="app-loading">
        <span className="brand-mark">R</span>
        <span>Loading Revilon AI</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="landing-page">
        <header className="landing-header">
          <button className="brand-button" type="button" onClick={() => navigate("/")}>
            <span className="brand-mark">R</span>
            <span>Revilon AI</span>
          </button>

          <div className="landing-actions">
            <button className="landing-sign-in" type="button" onClick={() => openAuth("login")}>
              Sign in
            </button>
            <button className="landing-sign-up" type="button" onClick={() => openAuth("register")}>
              Create account
            </button>
          </div>
        </header>

        <main className="landing-main">
          <div className="landing-content">
            <div className="landing-hero-mark">R</div>
            <h1>Revilon AI</h1>
            <p>
              A focused AI workspace for learning, writing, research, and clear
              problem-solving.
            </p>

            <form
              className="landing-composer"
              onSubmit={(event) => {
                event.preventDefault();
                openAuth("login");
              }}
            >
              <textarea
                rows="1"
                value={landingMessage}
                onChange={(event) => setLandingMessage(event.target.value)}
                placeholder="Write a message"
              />

              <button
                className="landing-send-button"
                type="submit"
                aria-label="Continue"
              >
                <ArrowUp size={18} />
              </button>
            </form>

            <p className="landing-small-note">
              Sign in to save conversations and continue your work.
            </p>
          </div>
        </main>

        {authOpen && (
          <Modal onClose={() => setAuthOpen(false)} className="auth-modal">
            <button className="modal-close" type="button" onClick={() => setAuthOpen(false)} aria-label="Close">
              <X size={18} />
            </button>

            <div className="modal-heading">
              <span className="modal-icon"><CircleUserRound size={20} /></span>
              <div>
                <h2>{authMode === "login" ? "Sign in" : "Create your account"}</h2>
                <p>
                  {authMode === "login"
                    ? "Continue to your Revilon AI workspace."
                    : "Create a secure Revilon AI workspace."}
                </p>
              </div>
            </div>

            <form onSubmit={submitAuth} className="form-stack">
              {authMode === "register" && (
                <div className="form-grid-two">
                  <label>
                    <span>First name</span>
                    <input
                      value={authForm.first_name}
                      onChange={(event) => setAuthForm({ ...authForm, first_name: event.target.value })}
                      autoComplete="given-name"
                      required
                    />
                  </label>
                  <label>
                    <span>Last name</span>
                    <input
                      value={authForm.last_name}
                      onChange={(event) => setAuthForm({ ...authForm, last_name: event.target.value })}
                      autoComplete="family-name"
                      required
                    />
                  </label>
                </div>
              )}

              <label>
                <span>Username</span>
                <input
                  value={authForm.username}
                  onChange={(event) => setAuthForm({ ...authForm, username: event.target.value })}
                  autoComplete="username"
                  required
                />
              </label>

              {authMode === "register" && (
                <label>
                  <span>Email address</span>
                  <input
                    type="email"
                    value={authForm.email}
                    onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })}
                    autoComplete="email"
                    required
                  />
                </label>
              )}

              <label>
                <span>Password</span>
                <input
                  type="password"
                  value={authForm.password}
                  onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
                  autoComplete={authMode === "login" ? "current-password" : "new-password"}
                  required
                />
              </label>

              {authMode === "register" && (
                <label>
                  <span>Confirm password</span>
                  <input
                    type="password"
                    value={authForm.confirm_password}
                    onChange={(event) => setAuthForm({ ...authForm, confirm_password: event.target.value })}
                    autoComplete="new-password"
                    required
                  />
                </label>
              )}

              {authError && <div className="form-message error-message">{authError}</div>}

              <button className="button button-light button-submit" type="submit" disabled={authBusy}>
                {authBusy
                  ? "Please wait..."
                  : authMode === "login"
                    ? "Sign in"
                    : "Create account"}
              </button>
            </form>

            <p className="auth-switch">
              {authMode === "login" ? "New to Revilon AI?" : "Already have an account?"}
              <button type="button" onClick={() => openAuth(authMode === "login" ? "register" : "login")}>
                {authMode === "login" ? "Create account" : "Sign in"}
              </button>
            </p>
          </Modal>
        )}

        {verificationOpen && (
          <Modal
            onClose={() => setVerificationOpen(false)}
            className="auth-modal verification-modal"
          >
            <button
              className="modal-close"
              type="button"
              onClick={() => setVerificationOpen(false)}
              aria-label="Close"
            >
              <X size={18} />
            </button>

            <div className="modal-heading">
              <span className="modal-icon"><Shield size={20} /></span>
              <div>
                <h2>Verify your email</h2>
                <p>Enter the six-digit code sent to your email address.</p>
              </div>
            </div>

            <p className="verification-email">{verificationEmail}</p>

            <form onSubmit={submitVerification} className="form-stack">
              <label>
                <span>Verification code</span>
                <input
                  className="verification-code-input"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength="6"
                  pattern="[0-9]{6}"
                  value={verificationCode}
                  onChange={(event) =>
                    setVerificationCode(
                      event.target.value.replace(/\D/g, "").slice(0, 6),
                    )
                  }
                  placeholder="000000"
                  autoFocus
                  required
                />
              </label>

              {verificationMessage && (
                <div className="form-message success-message">
                  {verificationMessage}
                </div>
              )}

              {verificationError && (
                <div className="form-message error-message">
                  {verificationError}
                </div>
              )}

              <button
                className="button button-light button-submit"
                type="submit"
                disabled={verificationBusy || verificationCode.length !== 6}
              >
                {verificationBusy ? "Please wait..." : "Verify email"}
              </button>
            </form>

            <div className="verification-actions">
              <button
                type="button"
                onClick={resendVerification}
                disabled={verificationBusy}
              >
                Send a new code
              </button>
              <button type="button" onClick={() => openAuth("login")}>
                Back to sign in
              </button>
            </div>
          </Modal>
        )}
      </div>
    );
  }

  if (isAdminPage) {
    if (!user.is_staff) {
      return null;
    }

    return (
      <div className="admin-shell">
        <aside className="admin-sidebar">
          <button className="brand-button" type="button" onClick={() => navigate("/admin")}>
            <span className="brand-mark">R</span>
            <span>Revilon AI</span>
          </button>

          <div className="admin-section-label">Administration</div>

          <nav className="admin-nav">
            <button className="active" type="button">
              <Users size={18} />
              User management
            </button>
          </nav>

          <div className="admin-sidebar-spacer" />

          <div className="account-area">
            {accountMenuOpen && (
              <AccountMenu
                user={user}
                adminPage
                onChat={() => navigate("/")}
                onLogout={logout}
              />
            )}
            <button
              className="account-trigger"
              type="button"
              onClick={() => setAccountMenuOpen((current) => !current)}
            >
              <Avatar user={user} />
              <span className="account-trigger-copy">
                <strong>{getDisplayName(user)}</strong>
                <small>Administrator</small>
              </span>
              <ChevronRight size={17} />
            </button>
          </div>
        </aside>

        <main className="admin-main">
          <header className="admin-header">
            <div>
              <span className="page-kicker">Administration</span>
              <h1>User management</h1>
              <p>Review and manage access to Revilon AI.</p>
            </div>
            <button className="button button-outline" type="button" onClick={() => navigate("/")}>
              <ArrowLeft size={16} />
              Open workspace
            </button>
          </header>

          <section className="admin-stat-grid">
            {adminSummary.map((item) => {
              const Icon = item.icon;
              return (
                <article className="admin-stat-card" key={item.label}>
                  <span className="stat-icon"><Icon size={19} /></span>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </article>
              );
            })}
          </section>

          <section className="admin-table-panel">
            <div className="admin-table-toolbar">
              <div>
                <h2>Users</h2>
                <p>{adminUsers.length} account{adminUsers.length === 1 ? "" : "s"} shown</p>
              </div>
              <label className="search-field">
                <Search size={17} />
                <input
                  value={adminSearch}
                  onChange={(event) => setAdminSearch(event.target.value)}
                  placeholder="Search users"
                />
              </label>
            </div>

            {adminError && <div className="panel-error">{adminError}</div>}

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Joined</th>
                    <th>Last sign in</th>
                    <th><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {adminBusy ? (
                    <tr>
                      <td colSpan="6" className="table-empty">Loading users...</td>
                    </tr>
                  ) : adminUsers.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="table-empty">No users found.</td>
                    </tr>
                  ) : (
                    adminUsers.map((adminUser) => (
                      <tr key={adminUser.id}>
                        <td>
                          <div className="table-user">
                            <Avatar user={adminUser} />
                            <div>
                              <strong>{adminUser.display_name}</strong>
                              <span>{adminUser.email || `@${adminUser.username}`}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className={`role-badge ${adminUser.is_staff ? "admin" : "member"}`}>
                            {adminUser.is_superuser
                              ? "Superuser"
                              : adminUser.is_staff
                                ? "Administrator"
                                : "Member"}
                          </span>
                        </td>
                        <td>
                          <span className={`status-badge ${adminUser.is_active ? "active" : "disabled"}`}>
                            <span />
                            {adminUser.is_active ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td>{formatDate(adminUser.date_joined)}</td>
                        <td>{formatDate(adminUser.last_login)}</td>
                        <td>
                          <button className="table-action" type="button" onClick={() => openAdminUser(adminUser)}>
                            <Edit3 size={16} />
                            Manage
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </main>

        {selectedAdminUser && adminEditForm && (
          <Modal onClose={() => setSelectedAdminUser(null)} className="admin-user-modal">
            <button className="modal-close" type="button" onClick={() => setSelectedAdminUser(null)} aria-label="Close">
              <X size={18} />
            </button>
            <div className="modal-heading">
              <Avatar user={selectedAdminUser} size="large" />
              <div>
                <h2>Manage user</h2>
                <p>Update account details, role, and access.</p>
              </div>
            </div>

            <form className="form-stack" onSubmit={saveAdminUser}>
              <div className="form-grid-two">
                <label>
                  <span>First name</span>
                  <input value={adminEditForm.first_name} onChange={(event) => setAdminEditForm({ ...adminEditForm, first_name: event.target.value })} required />
                </label>
                <label>
                  <span>Last name</span>
                  <input value={adminEditForm.last_name} onChange={(event) => setAdminEditForm({ ...adminEditForm, last_name: event.target.value })} required />
                </label>
              </div>
              <label>
                <span>Username</span>
                <input value={adminEditForm.username} onChange={(event) => setAdminEditForm({ ...adminEditForm, username: event.target.value })} required />
              </label>
              <label>
                <span>Email address</span>
                <input type="email" value={adminEditForm.email} onChange={(event) => setAdminEditForm({ ...adminEditForm, email: event.target.value })} required />
              </label>

              <div className="admin-toggle-list">
                <label className="toggle-row">
                  <div>
                    <strong>Active account</strong>
                    <span>Allow this user to sign in.</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={adminEditForm.is_active}
                    onChange={(event) => setAdminEditForm({ ...adminEditForm, is_active: event.target.checked })}
                    disabled={selectedAdminUser.id === user.id}
                  />
                </label>
                <label className="toggle-row">
                  <div>
                    <strong>Administrator access</strong>
                    <span>Allow access to user management.</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={adminEditForm.is_staff}
                    onChange={(event) => setAdminEditForm({ ...adminEditForm, is_staff: event.target.checked })}
                    disabled={!user.is_superuser || selectedAdminUser.id === user.id}
                  />
                </label>
              </div>

              {adminActionError && <div className="form-message error-message">{adminActionError}</div>}

              <div className="modal-actions modal-actions-between">
                <button
                  className="button button-danger-text"
                  type="button"
                  onClick={() => {
                    setSelectedAdminUser(null);
                    setAdminDeleteUser(selectedAdminUser);
                  }}
                  disabled={selectedAdminUser.id === user.id || selectedAdminUser.is_superuser}
                >
                  <Trash2 size={16} />
                  Delete user
                </button>
                <div>
                  <button className="button button-outline" type="button" onClick={() => setSelectedAdminUser(null)}>
                    Cancel
                  </button>
                  <button className="button button-light" type="submit" disabled={adminActionBusy}>
                    {adminActionBusy ? "Saving..." : "Save changes"}
                  </button>
                </div>
              </div>
            </form>
          </Modal>
        )}

        {adminDeleteUser && (
          <Modal onClose={() => setAdminDeleteUser(null)} className="confirm-modal">
            <span className="danger-icon"><Trash2 size={20} /></span>
            <h2>Delete user?</h2>
            <p>
              This permanently deletes <strong>{adminDeleteUser.display_name}</strong>,
              including all conversations and messages owned by this account.
            </p>
            {adminActionError && <div className="form-message error-message">{adminActionError}</div>}
            <div className="modal-actions">
              <button className="button button-outline" type="button" onClick={() => setAdminDeleteUser(null)}>
                Cancel
              </button>
              <button className="button button-danger" type="button" onClick={deleteAdminUser} disabled={adminActionBusy}>
                {adminActionBusy ? "Deleting..." : "Delete user"}
              </button>
            </div>
          </Modal>
        )}
      </div>
    );
  }

  return (
    <div className="workspace-shell">
      {mobileSidebarOpen && (
        <button className="mobile-overlay" type="button" onClick={() => setMobileSidebarOpen(false)} aria-label="Close sidebar" />
      )}

      <aside className={`chat-sidebar ${mobileSidebarOpen ? "open" : ""}`}>
        <div className="sidebar-top">
          <button className="brand-button" type="button" onClick={startNewConversation}>
            <span className="brand-mark">R</span>
            <span>Revilon AI</span>
          </button>
          <button className="mobile-close" type="button" onClick={() => setMobileSidebarOpen(false)} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>

        <button className="new-conversation-button" type="button" onClick={startNewConversation}>
          <Plus size={18} />
          New conversation
        </button>

        <div className="conversation-label">Conversations</div>

        <div className="conversation-list">
          {conversations.map((conversation) => (
            <div
              className={`conversation-item ${activeConversation?.id === conversation.id ? "active" : ""}`}
              key={conversation.id}
            >
              <button type="button" onClick={() => selectConversation(conversation)}>
                <span>{conversation.title}</span>
              </button>
              <button
                className="conversation-more"
                type="button"
                aria-label="Conversation options"
                onClick={(event) => toggleConversationMenu(event, conversation)}
              >
                <MoreHorizontal size={16} />
              </button>
              {conversationMenu?.id === conversation.id && createPortal(
                <div className="conversation-menu" style={{ top: conversationMenu.top, right: conversationMenu.right }}>
                  <button className="rename-action" type="button" onClick={() => {
                    setRenameConversation(conversation);
                    setRenameTitle(conversation.title);
                    setConversationMenu(null);
                  }}>
                    <Edit3 size={15} />
                    Rename
                  </button>
                  <button type="button" onClick={() => {
                    setDeleteConversation(conversation);
                    setConversationMenu(null);
                  }}>
                    <Trash2 size={15} />
                    Delete
                  </button>
                </div>,
                document.body,
              )}
            </div>
          ))}
        </div>

        <div className="sidebar-spacer" />

        <div className="account-area">
          {accountMenuOpen && (
            <AccountMenu
              user={user}
              onProfile={openProfile}
              onPassword={openPassword}
              onAdmin={() => navigate("/admin")}
              onLogout={logout}
            />
          )}
          <button
            className="account-trigger"
            type="button"
            onClick={() => setAccountMenuOpen((current) => !current)}
          >
            <Avatar user={user} />
            <span className="account-trigger-copy">
              <strong>{getDisplayName(user)}</strong>
              <small>Revilon AI Account</small>
            </span>
            <ChevronRight size={17} />
          </button>
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <button className="mobile-menu" type="button" onClick={() => setMobileSidebarOpen(true)} aria-label="Open sidebar">
            <Menu size={19} />
          </button>
          <span className="chat-header-mark">R</span>
          <span>{conversationTitle}</span>
        </header>

        <div className="chat-content">
          {messages.length === 0 ? (
            <section className="empty-chat">
              <span className="empty-chat-mark">R</span>
              <h1>What would you like to work on?</h1>
              <p>
                Use Revilon AI to understand difficult topics, organize your ideas,
                write clearly, and solve problems.
              </p>
            </section>
          ) : (
            <section className="message-list">
              {messages.map((message) => (
                <article className={`message-row ${message.role}`} key={message.id}>
                  {message.role === "assistant" && (
                    <span className="message-avatar"><Bot size={17} /></span>
                  )}
                  <div className="message-bubble">
                    {message.role === "assistant" ? (
                      <MarkdownMessage content={message.content} />
                    ) : (
                      message.content.split("\n").map((line, index) => (
                        <p key={`${message.id}-${index}`}>{line || <br />}</p>
                      ))
                    )}
                  </div>
                  {message.role === "user" && <Avatar user={user} size="small" />}
                </article>
              ))}

              {chatBusy && (
                <article className="message-row assistant">
                  <span className="message-avatar"><Bot size={17} /></span>
                  <div className="loading-message" aria-label="Revilon AI is responding">
                    <span /><span /><span />
                  </div>
                </article>
              )}
              <div ref={messageEndRef} />
            </section>
          )}
        </div>

        <div className="composer-region">
          {chatError && <div className="chat-error">{chatError}</div>}
          <form className="chat-composer" onSubmit={sendMessage}>
            <textarea
              value={messageText}
              onChange={(event) => setMessageText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Write a message"
              rows="1"
              disabled={chatBusy}
            />
            <button
              type={chatBusy ? "button" : "submit"}
              disabled={!chatBusy && !messageText.trim()}
              aria-label={chatBusy ? "Stop generating" : "Send message"}
              title={chatBusy ? "Stop generating" : "Send message"}
              onClick={chatBusy ? stopGenerating : undefined}
            >
              {chatBusy ? <Square size={15} fill="currentColor" /> : <ArrowUp size={19} />}
            </button>
          </form>
          <p className="chat-disclaimer">
            Revilon AI can make mistakes. Review important information.
          </p>
        </div>
      </main>

      {deleteConversation && (
        <Modal onClose={() => setDeleteConversation(null)} className="confirm-modal">
          <span className="danger-icon"><Trash2 size={20} /></span>
          <h2>Delete conversation?</h2>
          <p>This permanently deletes “{deleteConversation.title}” and all of its messages.</p>
          <div className="modal-actions">
            <button className="button button-outline" type="button" onClick={() => setDeleteConversation(null)}>
              Cancel
            </button>
            <button className="button button-danger" type="button" onClick={confirmDeleteConversation}>
              Delete
            </button>
          </div>
        </Modal>
      )}

      {renameConversation && (
        <Modal onClose={() => setRenameConversation(null)} className="rename-modal">
          <button className="modal-close" type="button" onClick={() => setRenameConversation(null)} aria-label="Close">
            <X size={18} />
          </button>
          <div className="modal-heading">
            <span className="modal-icon"><Edit3 size={19} /></span>
            <div>
              <h2>Rename conversation</h2>
              <p>Choose a clear name that will be easy to find later.</p>
            </div>
          </div>
          <form className="form-stack rename-form" onSubmit={submitRenameConversation}>
            <label>
              <span>Conversation name</span>
              <input autoFocus value={renameTitle} maxLength={255} onChange={(event) => setRenameTitle(event.target.value)} />
            </label>
            <div className="modal-actions">
              <button className="button button-outline" type="button" onClick={() => setRenameConversation(null)}>Cancel</button>
              <button className="button button-light" type="submit" disabled={renameBusy || !renameTitle.trim()}>
                {renameBusy ? "Saving..." : "Rename"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {profileOpen && (
        <Modal onClose={() => setProfileOpen(false)} className="profile-modal">
          <button className="modal-close" type="button" onClick={() => setProfileOpen(false)} aria-label="Close">
            <X size={18} />
          </button>
          <div className="modal-heading">
            <span className="modal-icon"><CircleUserRound size={20} /></span>
            <div>
              <h2>Edit profile</h2>
              <p>Update your personal and account details.</p>
            </div>
          </div>

          <form className="form-stack" onSubmit={submitProfile}>
            <div className="profile-picture-editor">
              <span className="profile-picture-preview">
                {profilePreview && !removeProfilePicture ? (
                  <img src={profilePreview} alt="Profile preview" />
                ) : (
                  <span>{getInitials(user)}</span>
                )}
              </span>
              <div>
                <strong>Profile picture</strong>
                <p>JPG, PNG, or WEBP. Maximum 5 MB.</p>
                <div className="picture-actions">
                  <input
                    ref={profileFileRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={chooseProfilePicture}
                    hidden
                  />
                  <button className="button button-outline button-small" type="button" onClick={() => profileFileRef.current?.click()}>
                    <Upload size={15} />
                    Upload picture
                  </button>
                  {(profilePreview || user.profile_picture) && !removeProfilePicture && (
                    <button className="button button-danger-text button-small" type="button" onClick={() => {
                      setProfilePictureFile(null);
                      setProfilePreview(null);
                      setRemoveProfilePicture(true);
                    }}>
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="form-grid-two">
              <label>
                <span>First name</span>
                <input value={profileForm.first_name} onChange={(event) => setProfileForm({ ...profileForm, first_name: event.target.value })} required />
              </label>
              <label>
                <span>Last name</span>
                <input value={profileForm.last_name} onChange={(event) => setProfileForm({ ...profileForm, last_name: event.target.value })} required />
              </label>
            </div>
            <label>
              <span>Username</span>
              <input value={profileForm.username} onChange={(event) => setProfileForm({ ...profileForm, username: event.target.value })} required />
            </label>
            <label>
              <span>Email address</span>
              <input type="email" value={profileForm.email} onChange={(event) => setProfileForm({ ...profileForm, email: event.target.value })} required />
            </label>

            {profileError && <div className="form-message error-message">{profileError}</div>}

            <div className="modal-actions">
              <button className="button button-outline" type="button" onClick={() => setProfileOpen(false)}>
                Cancel
              </button>
              <button className="button button-light" type="submit" disabled={profileBusy}>
                {profileBusy ? "Saving..." : "Save changes"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {passwordOpen && (
        <Modal onClose={() => setPasswordOpen(false)} className="password-modal">
          <button className="modal-close" type="button" onClick={() => setPasswordOpen(false)} aria-label="Close">
            <X size={18} />
          </button>
          <div className="modal-heading">
            <span className="modal-icon"><KeyRound size={20} /></span>
            <div>
              <h2>Change password</h2>
              <p>Choose a strong password you do not use elsewhere.</p>
            </div>
          </div>

          <form className="form-stack" onSubmit={submitPassword}>
            <label>
              <span>Current password</span>
              <input type="password" value={passwordForm.current_password} onChange={(event) => setPasswordForm({ ...passwordForm, current_password: event.target.value })} autoComplete="current-password" required />
            </label>
            <label>
              <span>New password</span>
              <input type="password" value={passwordForm.new_password} onChange={(event) => setPasswordForm({ ...passwordForm, new_password: event.target.value })} autoComplete="new-password" required />
            </label>
            <label>
              <span>Confirm new password</span>
              <input type="password" value={passwordForm.confirm_password} onChange={(event) => setPasswordForm({ ...passwordForm, confirm_password: event.target.value })} autoComplete="new-password" required />
            </label>

            {passwordError && <div className="form-message error-message">{passwordError}</div>}
            {passwordSuccess && <div className="form-message success-message">{passwordSuccess}</div>}

            <div className="modal-actions">
              <button className="button button-outline" type="button" onClick={() => setPasswordOpen(false)}>
                Cancel
              </button>
              <button className="button button-light" type="submit" disabled={passwordBusy}>
                {passwordBusy ? "Updating..." : "Update password"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}


export default App;
