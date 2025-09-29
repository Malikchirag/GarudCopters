import './SplineBanner.css';
import Spline from '@splinetool/react-spline';
import { useEffect, useRef } from 'react';

const SplineBanner = ({ scene }) => {
    const containerRef = useRef(null);

    useEffect(() => {
        const container = containerRef.current;

        const handleWheel = (e) => {
            // Check if the user is at the top or bottom of the container
            const atTop = container.scrollTop === 0;
            const atBottom = container.scrollHeight - container.scrollTop === container.clientHeight;

            if ((e.deltaY < 0 && atTop) || (e.deltaY > 0 && atBottom)) {
                // Let the scroll propagate to the window
                return;
            }

            // Prevent scroll from being captured by inner elements unnecessarily
            e.stopPropagation();
        };

        if (container) {
            container.addEventListener('wheel', handleWheel, { passive: false });
        }

        return () => {
            if (container) {
                container.removeEventListener('wheel', handleWheel);
            }
        };
    }, []);

    return (
        <div className="spline-container fade-in" ref={containerRef}>
            <Spline id="home-spline" scene={scene} />
        </div>
    );
};

export default SplineBanner;
