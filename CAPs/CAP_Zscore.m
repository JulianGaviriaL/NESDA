function [CAP_z] = CAP_Zscore(CAP)
    for i = 1:size(CAP,1)
        [a,b] = hist(CAP(i,:), 100);
        aind = find(a == max(a));
        med  = b(aind(1));
        CAP_z(i,:) = (CAP(i,:)-med)/sqrt((sum((CAP(i,:)-med).^2))/length(CAP(i,:)));    % normalization copied from Isik
    end
end