import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./styles.css";

const RouteHost = { template: "<div />" };

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: RouteHost },
    { path: "/cars", component: RouteHost },
    { path: "/reviews", component: RouteHost },
    { path: "/community", component: RouteHost },
    { path: "/market", component: RouteHost },
    { path: "/rankings", component: RouteHost },
    { path: "/articles/:id", component: RouteHost },
    { path: "/messages", component: RouteHost },
    { path: "/messages/:id", component: RouteHost },
    { path: "/notifications", component: RouteHost },
    { path: "/reset-password/:uid/:token", component: RouteHost },
    { path: "/post/:id", component: RouteHost },
    { path: "/cars/:slug/community", component: RouteHost },
    { path: "/cars/:slug", component: RouteHost },
    { path: "/shops/:slug", component: RouteHost },
    { path: "/clubs/:slug", component: RouteHost },
    { path: "/events/:slug", component: RouteHost },
    { path: "/market/:slug", component: RouteHost },
    { path: "/guides/:id", component: RouteHost },
    { path: "/topics/:slug", component: RouteHost },
    { path: "/:pathMatch(.*)*", component: RouteHost },
  ],
});

createApp(App).use(router).mount("#root");
