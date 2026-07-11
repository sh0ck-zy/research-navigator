import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { ProjectList } from "./pages/ProjectList";
import { NewProject } from "./pages/NewProject";

// Library and Board routes land in CP2/CP5. Placeholders keep the shell honest.
export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <ProjectList /> },
      { path: "/projects/new", element: <NewProject /> },
      { path: "/projects/:id/library", element: <div className="p-8">Library — coming in CP2</div> },
      { path: "/projects/:id/board", element: <div className="p-8">Board — coming in CP5</div> },
    ],
  },
]);
