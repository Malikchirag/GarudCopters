import './Statistics.css';
import SplineBannerNoMouse from '../../components/SplineBannerNoMouse/SplineBannerNoMouse';
import DisasterDeathsChart from '../../components/DisasterDeathsChart/DisasterDeathsChart';

const Statistics = () => {
    return (
        <div className='home-banner-2'>
            <SplineBannerNoMouse scene={'https://prod.spline.design/70SsCJNkUC7xjekU/scene.splinecode'} />
            <DisasterDeathsChart />
        </div>
    );
}

export default Statistics;

