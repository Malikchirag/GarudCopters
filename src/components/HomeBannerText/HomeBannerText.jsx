import './HomeBannerText.css';
import GetStartedButton from '../../components/GetStartedButton/GetStartedButton';

const HomeSplineBanner = ({Heading, Tagline}) => {
    return(
        <div id='home-banner-text'>
            <h1 id='banner-heading'>{Heading}</h1>
            <p className='text'>{Tagline}</p>
            <GetStartedButton />
            
        </div>
    )
}

export default HomeSplineBanner;