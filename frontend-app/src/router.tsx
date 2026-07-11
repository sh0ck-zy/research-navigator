import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { ProjectList } from "./pages/ProjectList";
import { NewProject } from "./pages/NewProject";
import { ProjectLayout } from "./pages/ProjectLayout";
import { Library } from "./pages/Library";

// The Board lands in CP5. Placeholder keeps the shell honest.
export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <ProjectList /> },
      { path: "/projects/new", element: <NewProject /> },
      {
        path: "/projects/:id",
        element: <ProjectLayout />,
        children: [
          { path: "library", element: <Library /> },
          { path: "board", element: <div className="py-8 text-neutral-500">Board — coming in CP5</div> },
        ],
      },
    ],
  },
]);
