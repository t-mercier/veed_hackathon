import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/hooks/useAuth";
import Layout from "./components/Layout";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Profile from "./pages/Profile";
import Premium from "./pages/Premium";
import Concepts from "./pages/Concepts";
import RepoExplainer from "./pages/RepoExplainer";
import PromptExplainer from "./pages/PromptExplainer";
import ConceptAlgoExplainer from "./pages/ConceptAlgoExplainer";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Index />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/concepts" element={<Concepts />} />
              <Route path="/premium" element={<Premium />} />
              <Route path="/repo/:jobId" element={<RepoExplainer />} />
              <Route path="/prompt/:jobId" element={<PromptExplainer />} />
              <Route path="/concept/:jobId" element={<ConceptAlgoExplainer />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
