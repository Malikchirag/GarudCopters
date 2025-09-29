import './InfoCard.css';

const InfoCard = ({title, heading, text, src}) => {
    return(
        <div id='info-card'>
            <img src={src} alt='img' id='info-card-img'/>
            <h2 id='info-card-title'>{title}</h2>
            <h1 id='info-card-heading'>{heading}</h1>
            <p id='info-card-text'>{text}</p>
        </div>
    )
}

export default InfoCard;