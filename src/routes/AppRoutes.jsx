import { Routes, Route } from "react-router-dom";
import Home from "../pages/home/Home";
import Statistics from "../pages/statistics/Statistics";
import Header from "../layouts/header/Header";


const AppRoutes = () => {
    return (
        <Routes>
            <Route path="/" element={<Header />}>
                <Route index element={<Home />} />
                <Route path="statistics" element={<Statistics />} />
            </Route>
        </Routes>
    );
};

export default AppRoutes;