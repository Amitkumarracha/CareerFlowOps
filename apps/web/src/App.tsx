import { BrowserRouter, Route, Routes, Link } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Overview, JobsPage, JobDetail } from "./pages/Jobs";
import { ProfilePage, ResumePage, RecommendedPage } from "./pages/Candidate";
import { ApplicationsPage } from "./pages/Applications";
import { TpoPage, MlopsPage, AdminPage } from "./pages/Operations";
export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="jobs/:id" element={<JobDetail />} />
          <Route path="recommended" element={<RecommendedPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="resume" element={<ResumePage />} />
          <Route path="applications" element={<ApplicationsPage />} />
          <Route path="tpo" element={<TpoPage />} />
          <Route path="mlops" element={<MlopsPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route
            path="*"
            element={
              <div className="notice">
                <h1>Page not found</h1>
                <Link to="/jobs">Explore opportunities</Link>
              </div>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
