import { createBrowserRouter } from "react-router";
import Root from "./Root";
import Home from "./screens/Home";
import Upload from "./screens/Upload";
import Verdict from "./screens/Verdict";
import Leaderboard from "./screens/Leaderboard";
import RefProfile from "./screens/RefProfile";
import Feed from "./screens/Feed";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Home },
      { path: "upload", Component: Upload },
      { path: "verdict/:id", Component: Verdict },
      { path: "leaderboard", Component: Leaderboard },
      { path: "ref/:slug", Component: RefProfile },
      { path: "feed", Component: Feed },
    ],
  },
]);
