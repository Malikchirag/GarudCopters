import { Outlet, NavLink, useLocation } from "react-router-dom";
import { useState, useEffect, useRef } from 'react';
import './Header.css';

const Header = () => {
    const [isDarkSection, setIsDarkSection] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const location = useLocation();
    const headerRef = useRef(null);
    
    // Function to check if the header is over a dark section
    const checkSectionColor = () => {
        if (!headerRef.current) return;
        
        // Get the element directly under the header
        const headerRect = headerRef.current.getBoundingClientRect();
        const headerCenter = {
            x: headerRect.left + headerRect.width / 2,
            y: headerRect.top + headerRect.height / 2
        };
        
        // Use elementFromPoint to get the actual element under the header
        // We temporarily hide the header to get the element beneath it
        headerRef.current.style.pointerEvents = 'none';
        const elementBeneath = document.elementFromPoint(headerCenter.x, headerCenter.y);
        headerRef.current.style.pointerEvents = '';
        
        // Check if the element or its parents have the 'dark-bg' class
        if (elementBeneath) {
            let current = elementBeneath;
            while (current && current !== document.body) {
                if (current.classList.contains('dark-bg')) {
                    setIsDarkSection(true);
                    return;
                }
                current = current.parentElement;
            }
        }
        
        setIsDarkSection(false);
    };
    
    // Add scroll event listener
    useEffect(() => {
        window.addEventListener('scroll', checkSectionColor);
        // Initial check
        checkSectionColor();
        
        return () => {
            window.removeEventListener('scroll', checkSectionColor);
        };
    }, [location.pathname]);
    
    const toggleMenu = () => {
        setMenuOpen(!menuOpen);
    };

    return (
        <>
            <div id="container-div-header" className={isDarkSection ? 'dark-section' : ''} ref={headerRef}>
                <header id="header-div">
                    <div className="hamburger" onClick={toggleMenu}>
                        <div className={`bar ${menuOpen ? 'open' : ''}`}></div>
                        <div className={`bar ${menuOpen ? 'open' : ''}`}></div>
                        <div className={`bar ${menuOpen ? 'open' : ''}`}></div>
                    </div>
                    <nav className={menuOpen ? 'open' : ''}>
                        <ul id="navigation-buttons">
                            <li><NavLink to="/" end className={({isActive}) => isActive ? 'h-nav-btns active' : 'h-nav-btns'} onClick={() => setMenuOpen(false)}>Home</NavLink></li>
                            <li><NavLink to="/statistics" end className={({isActive}) => isActive ? 'h-nav-btns active' : 'h-nav-btns'} onClick={() => setMenuOpen(false)}>Statistics</NavLink></li>
                            {/* <li><NavLink to="/newsletter" end className={({isActive}) => isActive ? 'h-nav-btns active' : 'h-nav-btns'} onClick={() => setMenuOpen(false)}>Newsletter</NavLink></li>
                            <li><span className='h-nav-btns'>Contact</span></li> */}
                        </ul>
                    </nav>
                </header>
            </div>
            <Outlet /> 
        </>
    );
}

export default Header;