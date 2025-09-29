import './GetStartedButton.css';
import { Outlet, Link } from "react-router-dom"

const GetStartedButton = () => {
    return (
        <>
            <a id='get-started-button' href='/signup'>
                <p id='get-started-button-text'>Get Started →</p>
            </a>
            <Outlet />
        </>
    )
}

export default GetStartedButton;