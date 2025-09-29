import './SplineBannerNoMouse.css';
import Spline from '@splinetool/react-spline';

const SplineBannerNoMouse = ({ scene }) => {
    return (
        <div className="fade-in-container">
            <Spline
                id='nomouse-spline'
                scene={scene}
            />
            {/* <spline-viewer url={scene}></spline-viewer> */}
        </div>
    );
};

export default SplineBannerNoMouse;